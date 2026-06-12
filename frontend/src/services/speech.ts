import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";
import { request } from "./api";

export type SpeechTokenResponse = {
  token: string;
  region: string;
  language: string;
  expires_in: number;
};

export async function getSpeechToken() {
  return request<SpeechTokenResponse>("/speech/token");
}

export async function recognizeSpeechOnce(options: {
  token: string;
  region: string;
  language: string;
  onFinalTranscript: (text: string) => void;
}) {
  const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(
    options.token,
    options.region
  );
  speechConfig.speechRecognitionLanguage = options.language;

  const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
  const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

  return new Promise<void>((resolve, reject) => {
    recognizer.recognizeOnceAsync(
      (result) => {
        try {
          if (
            result.reason === SpeechSDK.ResultReason.RecognizedSpeech &&
            result.text.trim()
          ) {
            options.onFinalTranscript(result.text.trim());
          } else if (result.reason === SpeechSDK.ResultReason.NoMatch) {
            reject(new Error("No speech was recognized"));
            return;
          }
          resolve();
        } finally {
          recognizer.close();
        }
      },
      (error) => {
        recognizer.close();
        reject(new Error(error));
      }
    );
  });
}
