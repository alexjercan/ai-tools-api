{self}: {
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.services.ai-tools-api;
  model = pkgs.fetchurl {
    name = "ggml-large-v3-turbo-q5_0.bin";
    url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin";
    hash = "sha256-OUIhcJzVrR9AxG5gMcphvOiJMebgiMGIKUxtWlX/p+I=";
  };
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
  deployedVoiceAssets = pkgs.runCommand "ai-tools-api-deployed-voice" {} ''
    mkdir -p "$out"
    ln -s ${cfg.piperModel} "$out/en_US-lessac-medium.onnx"
    ln -s ${cfg.piperConfig} "$out/en_US-lessac-medium.onnx.json"
  '';
  deployedVoiceModel = "${deployedVoiceAssets}/en_US-lessac-medium.onnx";
  deployedVoiceConfig = "${deployedVoiceAssets}/en_US-lessac-medium.onnx.json";
  whisperReady = pkgs.writeShellScript "ai-tools-api-whisper-ready" ''
    for _ in $(${pkgs.coreutils}/bin/seq 1 600); do
      if ${lib.getExe' pkgs.netcat-openbsd "nc"} -z 127.0.0.1 ${toString cfg.whisperPort}; then
        exit 0
      fi
      ${pkgs.coreutils}/bin/sleep 0.05
    done
    exit 1
  '';
  piperPackage =
    (pkgs.piper-tts.override {
      withTrain = false;
      withHTTP = false;
      withAlignment = false;
    }).overrideAttrs (old: {
      pname = "ai-tools-api-piper";
      patches = (old.patches or []) ++ [./piper-stdout.patch];
    });
in {
  options.services.ai-tools-api = {
    enable = lib.mkEnableOption "the private AI tools API";
    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.ai-tools-api;
      description = "Complete API runtime package.";
    };
    host = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "API bind address.";
    };
    port = lib.mkOption {
      type = lib.types.port;
      default = 10300;
      description = "API TCP port.";
    };
    whisperPackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.whisper-cpp-vulkan;
      description = "Package providing whisper-server.";
    };
    whisperModel = lib.mkOption {
      type = lib.types.package;
      default = model;
      description = "Whisper GGML model.";
    };
    whisperPort = lib.mkOption {
      type = lib.types.port;
      default = 10301;
      description = "Private loopback Whisper port.";
    };
    piperPackage = lib.mkOption {
      type = lib.types.package;
      default = piperPackage;
      description = "Package providing Piper.";
    };
    piperModel = lib.mkOption {
      type = lib.types.package;
      default = voiceModel;
      description = "Piper voice model.";
    };
    piperConfig = lib.mkOption {
      type = lib.types.package;
      default = voiceConfig;
      description = "Piper voice configuration.";
    };
    sttConcurrency = lib.mkOption {
      type = lib.types.ints.between 1 32;
      default = 2;
      description = "Maximum concurrent transcription requests.";
    };
    ttsConcurrency = lib.mkOption {
      type = lib.types.ints.between 1 32;
      default = 2;
      description = "Maximum concurrent synthesis requests.";
    };
    sttTimeout = lib.mkOption {
      type = lib.types.ints.between 1 600;
      default = 120;
      description = "Transcription timeout in seconds.";
    };
    ttsTimeout = lib.mkOption {
      type = lib.types.ints.between 1 600;
      default = 60;
      description = "Synthesis timeout in seconds.";
    };
  };

  config = lib.mkIf cfg.enable {
    systemd.user.services.ai-tools-api-whisper = {
      Unit = {
        Description = "Private loopback Whisper server";
        StartLimitIntervalSec = 60;
        StartLimitBurst = 3;
      };
      Service = {
        Type = "simple";
        ExecStart = lib.escapeShellArgs [
          (lib.getExe' cfg.whisperPackage "whisper-server")
          "--model"
          (toString cfg.whisperModel)
          "--host"
          "127.0.0.1"
          "--port"
          (toString cfg.whisperPort)
          "--inference-path"
          "/private-inference"
          "--language"
          "auto"
        ];
        Restart = "on-failure";
        RestartSec = 5;
        RuntimeDirectory = "ai-tools-api-whisper";
        WorkingDirectory = "%t/ai-tools-api-whisper";
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        UMask = "0077";
        TimeoutStopSec = 10;
      };
      Install.WantedBy = ["default.target"];
    };

    systemd.user.services.ai-tools-api = {
      Unit = {
        Description = "Private AI tools API";
        Requires = ["ai-tools-api-whisper.service"];
        After = ["ai-tools-api-whisper.service"];
        StartLimitIntervalSec = 60;
        StartLimitBurst = 3;
      };
      Service = {
        Type = "simple";
        ExecStartPre = whisperReady;
        ExecStart = lib.getExe cfg.package;
        Environment = [
          "AI_TOOLS_API_EXTERNAL_WHISPER=1"
          "AI_TOOLS_API_HOST=${cfg.host}"
          "AI_TOOLS_API_PORT=${toString cfg.port}"
          "AI_TOOLS_API_WHISPER_URL=http://127.0.0.1:${toString cfg.whisperPort}/private-inference"
          "AI_TOOLS_API_PIPER=${lib.getExe cfg.piperPackage}"
          "AI_TOOLS_API_PIPER_MODEL=${deployedVoiceModel}"
          "AI_TOOLS_API_PIPER_CONFIG=${deployedVoiceConfig}"
          "AI_TOOLS_API_STT_CONCURRENCY=${toString cfg.sttConcurrency}"
          "AI_TOOLS_API_TTS_CONCURRENCY=${toString cfg.ttsConcurrency}"
          "AI_TOOLS_API_STT_TIMEOUT=${toString cfg.sttTimeout}"
          "AI_TOOLS_API_TTS_TIMEOUT=${toString cfg.ttsTimeout}"
        ];
        Restart = "on-failure";
        RestartSec = 5;
        RuntimeDirectory = "ai-tools-api";
        WorkingDirectory = "%t/ai-tools-api";
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        UMask = "0077";
        TimeoutStopSec = 10;
      };
      Install.WantedBy = ["default.target"];
    };
  };
}
