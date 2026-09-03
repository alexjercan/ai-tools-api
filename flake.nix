{
  description = "Private API for small reusable AI-backed tools";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
    };
  };

  outputs = inputs @ {
    self,
    flake-parts,
    home-manager,
    nixpkgs,
    pyproject-nix,
    pyproject-build-systems,
    uv2nix,
    ...
  }: let
    workspace = uv2nix.lib.workspace.loadWorkspace {workspaceRoot = ./.;};
    pythonOverlay = workspace.mkPyprojectOverlay {sourcePreference = "wheel";};
    editableOverlay = workspace.mkEditablePyprojectOverlay {root = "$REPO_ROOT";};
  in
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux" "aarch64-linux"];

      perSystem = {
        pkgs,
        system,
        ...
      }: let
        lib = pkgs.lib;
        python = pkgs.python3;
        pythonBase = pkgs.callPackage pyproject-nix.build.packages {inherit python;};
        pythonSet = pythonBase.overrideScope (lib.composeManyExtensions [
          pyproject-build-systems.overlays.wheel
          pythonOverlay
        ]);
        editablePythonSet = pythonSet.overrideScope editableOverlay;
        devEnv = editablePythonSet.mkVirtualEnv "ai-tools-api-dev" workspace.deps.all;
        runtimeEnv = pythonSet.mkVirtualEnv "ai-tools-api-runtime" workspace.deps.default;
        inherit (pkgs.callPackages pyproject-nix.build.util {}) mkApplication;

        whisperModel = pkgs.fetchurl {
          name = "ggml-large-v3-turbo-q5_0.bin";
          url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin";
          hash = "sha256-OUIhcJzVrR9AxG5gMcphvOiJMebgiMGIKUxtWlX/p+I=";
        };
        llamaModels = import ./nix/llama-models.nix {inherit pkgs;};
        voiceModel = pkgs.fetchurl {
          name = "en_US-lessac-medium.onnx";
          url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx";
          hash = "sha256-Xv4J5pkCGHgnr2RuGm6dJp3udp+Yd9F7FrG0buqvAZ8=";
        };
        voiceConfig = pkgs.fetchurl {
          name = "en_US-lessac-medium.onnx.json";
          url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json";
          hash = "sha256-7+GcQXvtBV8taZCCSMa6ZQ+hNbyGiw5quz2hgdq2kKA=";
        };
        voiceAssets = pkgs.runCommand "ai-tools-api-en_US-lessac-medium" {} ''
          mkdir -p "$out/share/ai-tools-api/voices"
          ln -s ${voiceModel} "$out/share/ai-tools-api/voices/en_US-lessac-medium.onnx"
          ln -s ${voiceConfig} "$out/share/ai-tools-api/voices/en_US-lessac-medium.onnx.json"
        '';
        voiceModelPath = "${voiceAssets}/share/ai-tools-api/voices/en_US-lessac-medium.onnx";
        voiceConfigPath = "${voiceAssets}/share/ai-tools-api/voices/en_US-lessac-medium.onnx.json";
        piperPackage =
          (pkgs.piper-tts.override {
            withTrain = false;
            withHTTP = false;
            withAlignment = false;
          }).overrideAttrs (old: {
            pname = "ai-tools-api-piper";
            patches = (old.patches or []) ++ [./nix/piper-stdout.patch];
          });
        pythonApplication = mkApplication {
          venv = runtimeEnv;
          package = pythonSet.ai-tools-api;
        };
        wrappedApi = pythonApplication.overrideAttrs (old: {
          nativeBuildInputs = (old.nativeBuildInputs or []) ++ [pkgs.makeWrapper];
          postFixup =
            (old.postFixup or "")
            + ''
              wrapProgram "$out/bin/ai-tools-api" \
                --set-default AI_TOOLS_API_PIPER ${lib.getExe piperPackage} \
                --set-default AI_TOOLS_API_PIPER_MODEL ${voiceModelPath} \
                --set-default AI_TOOLS_API_PIPER_CONFIG ${voiceConfigPath}
            '';
        });
        application = pkgs.writeShellApplication {
          name = "ai-tools-api";
          runtimeInputs = [pkgs.netcat-openbsd];
          text = ''
            : "''${AI_TOOLS_API_WHISPER:=${lib.getExe' pkgs.whisper-cpp-vulkan "whisper-server"}}"
            : "''${AI_TOOLS_API_WHISPER_MODEL:=${whisperModel}}"
            : "''${AI_TOOLS_API_WHISPER_PORT:=10301}"
            : "''${AI_TOOLS_API_WHISPER_URL:=http://127.0.0.1:''${AI_TOOLS_API_WHISPER_PORT}/private-inference}"
            : "''${AI_TOOLS_API_LLAMA:=${lib.getExe' pkgs.llama-cpp-vulkan "llama-server"}}"
            : "''${AI_TOOLS_API_LLAMA_MODELS_PRESET:=${llamaModels.preset}}"
            : "''${AI_TOOLS_API_LLAMA_PORT:=10302}"
            : "''${AI_TOOLS_API_LLAMA_URL:=http://127.0.0.1:''${AI_TOOLS_API_LLAMA_PORT}/v1/chat/completions}"
            export AI_TOOLS_API_WHISPER_URL AI_TOOLS_API_LLAMA_URL

            whisper_pid=
            llama_pid=
            api_pid=
            if [ "''${AI_TOOLS_API_EXTERNAL_WHISPER:-0}" != 1 ]; then
              "$AI_TOOLS_API_WHISPER" \
                --model "$AI_TOOLS_API_WHISPER_MODEL" \
                --host 127.0.0.1 \
                --port "$AI_TOOLS_API_WHISPER_PORT" \
                --inference-path /private-inference \
                --language auto &
              whisper_pid=$!
            fi
            if [ "''${AI_TOOLS_API_EXTERNAL_LLAMA:-0}" != 1 ]; then
              "$AI_TOOLS_API_LLAMA" \
                --models-preset "$AI_TOOLS_API_LLAMA_MODELS_PRESET" \
                --host 127.0.0.1 \
                --port "$AI_TOOLS_API_LLAMA_PORT" \
                --ctx-size 128000 &
              llama_pid=$!
            fi
            stop_child() {
              child_pid=$1
              if [ -z "$child_pid" ]; then return; fi
              kill -TERM "$child_pid" 2>/dev/null || true
              for _ in $(seq 1 60); do
                kill -0 "$child_pid" 2>/dev/null || break
                sleep 0.05
              done
              kill -KILL "$child_pid" 2>/dev/null || true
              wait "$child_pid" 2>/dev/null || true
            }
            stop() {
              if [ -n "$api_pid" ]; then kill -TERM "$api_pid" 2>/dev/null || true; fi
              stop_child "$whisper_pid"
              stop_child "$llama_pid"
            }
            ready() {
              child_pid=$1
              child_port=$2
              if [ -z "$child_pid" ]; then return 0; fi
              for _ in $(seq 1 600); do
                if ! kill -0 "$child_pid" 2>/dev/null; then return 1; fi
                if nc -z 127.0.0.1 "$child_port"; then return 0; fi
                sleep 0.05
              done
              return 1
            }
            trap stop EXIT INT TERM
            ready "$whisper_pid" "$AI_TOOLS_API_WHISPER_PORT"
            ready "$llama_pid" "$AI_TOOLS_API_LLAMA_PORT"
            ${lib.getExe wrappedApi} "$@" & api_pid=$!
            wait "$api_pid"
          '';
          meta = {
            description = "Run the complete private AI tools API";
            mainProgram = "ai-tools-api";
            platforms = lib.platforms.linux;
          };
        };
        sourceCheck = name: command:
          pkgs.runCommand "ai-tools-api-${name}" {
            nativeBuildInputs = [devEnv pkgs.alejandra];
            src = ./.;
          } ''
            cp -r "$src" work
            chmod -R +w work
            cd work
            export HOME="$TMPDIR"
            export REPO_ROOT="$PWD"
            export PYTHONPATH=
            ${command}
            touch "$out"
          '';
        enabledHome = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            self.homeModules.default
            {
              home.username = "api-test";
              home.homeDirectory = "/tmp/api-test";
              home.stateVersion = "24.05";
              services.ai-tools-api = {
                enable = true;
                llamaModelsPreset = pkgs.writeText "test-llama-models.ini" ''
                  [test]
                  model=/nix/store/test-model.gguf
                  alias=test
                '';
              };
            }
          ];
        };
        disabledHome = home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          modules = [
            self.homeModules.default
            {
              home.username = "api-test";
              home.homeDirectory = "/tmp/api-test";
              home.stateVersion = "24.05";
            }
          ];
        };
      in {
        formatter = pkgs.alejandra;
        packages = {
          default = application;
          ai-tools-api = application;
          ai-tools-api-core = wrappedApi;
        };
        apps = {
          default = {
            type = "app";
            program = "${application}/bin/ai-tools-api";
            meta.description = "Run the complete private AI tools API";
          };
          ai-tools-api = {
            type = "app";
            program = "${application}/bin/ai-tools-api";
            meta.description = "Run the complete private AI tools API";
          };
        };
        devShells.default = pkgs.mkShell {
          packages = [devEnv pkgs.uv pkgs.curl pkgs.jq pkgs.alejandra pkgs.nixd];
          env = {
            UV_NO_SYNC = "1";
            UV_PYTHON = editablePythonSet.python.interpreter;
            UV_PYTHON_DOWNLOADS = "never";
          };
          shellHook = ''
            unset PYTHONPATH
            export REPO_ROOT=$(git rev-parse --show-toplevel)
            source ${devEnv}/bin/activate
          '';
        };
        checks = {
          format = sourceCheck "format" "ruff format --check . && alejandra --check flake.nix nix";
          lint = sourceCheck "lint" "ruff check .";
          typing = sourceCheck "typing" "mypy src";
          unit = sourceCheck "unit" "pytest";
          module-evaluation = assert !(disabledHome.config.systemd.user.services ? ai-tools-api);
          assert !(disabledHome.config.systemd.user.services ? ai-tools-api-whisper);
          assert !(disabledHome.config.systemd.user.services ? ai-tools-api-llama);
          assert enabledHome.config.systemd.user.services ? ai-tools-api;
          assert enabledHome.config.systemd.user.services ? ai-tools-api-whisper;
          assert enabledHome.config.systemd.user.services ? ai-tools-api-llama;
          assert enabledHome.config.systemd.user.services.ai-tools-api.Service.ProtectHome == "tmpfs";
          assert enabledHome.config.systemd.user.services.ai-tools-api-whisper.Service.ProtectHome == "tmpfs";
          assert enabledHome.config.systemd.user.services.ai-tools-api-llama.Service.ProtectHome == "tmpfs";
          assert enabledHome.config.services.ai-tools-api.whisperPort == 10301;
          assert enabledHome.config.services.ai-tools-api.llamaPort == 10302;
            pkgs.runCommand "ai-tools-api-module-evaluation" {
              enabled = enabledHome.activationPackage;
              disabled = disabledHome.activationPackage;
            } ''
              test -e "$enabled" -a -e "$disabled"
              touch "$out"
            '';
        };
      };

      flake.homeModules.default = import ./nix/module.nix {inherit self;};
    };
}
