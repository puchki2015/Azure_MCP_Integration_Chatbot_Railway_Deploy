import { Button } from "../ui/Button";

export function VoiceInputButton({
  listening,
  onClick,
  disabled = false
}: {
  listening: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <Button
      variant={listening ? "primary" : "secondary"}
      className="voice-input-button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={listening}
      title={listening ? "Stop voice input" : "Start voice input"}
    >
      {listening ? "Listening…" : "🎤 Voice"}
    </Button>
  );
}
