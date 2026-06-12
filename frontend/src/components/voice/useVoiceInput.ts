import { useCallback, useEffect, useState } from "react";
import { getSpeechToken, recognizeSpeechOnce } from "../../services/speech";

export function useVoiceInput(onTranscript: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async () => {
    try {
      setError(null);
      if (listening) {
        return;
      }

      const token = await getSpeechToken();
      setListening(true);
      await recognizeSpeechOnce({
        token: token.token,
        region: token.region,
        language: token.language,
        onFinalTranscript: (text) => {
          onTranscript(text);
        }
      });
      setListening(false);
    } catch (ex) {
      setError(ex instanceof Error ? ex.message : "Voice input failed");
      setListening(false);
    }
  }, [listening, onTranscript]);

  useEffect(() => {
    return () => {
      setListening(false);
    };
  }, []);

  return {
    listening,
    error,
    start,
  };
}
