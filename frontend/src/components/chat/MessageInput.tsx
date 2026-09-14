"use client";

import { ArrowUp, Mic, Square } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface MessageInputProps {
  onSend: (query: string) => void;
  disabled?: boolean;
}

function getSpeechRecognitionCtor(): (new () => SpeechRecognition) | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [value, setValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    setSpeechSupported(getSpeechRecognitionCtor() !== null);
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleToggleListening() {
    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    const SpeechRecognitionCtor = getSpeechRecognitionCtor();
    if (!SpeechRecognitionCtor) return;

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      setValue(transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2" aria-label="Send a message">
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={isListening ? "Listening…" : "Ask a question..."}
        disabled={disabled}
        aria-label="Message"
        className="rounded-full"
      />
      {speechSupported && (
        <Button
          type="button"
          variant={isListening ? "default" : "ghost"}
          size="icon"
          className="shrink-0 rounded-full"
          onClick={handleToggleListening}
          disabled={disabled}
          aria-pressed={isListening}
          aria-label={isListening ? "Stop voice input" : "Start voice input"}
        >
          {isListening ? <Square className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </Button>
      )}
      <Button
        type="submit"
        size="icon"
        className="shrink-0 rounded-full"
        disabled={disabled || !value.trim()}
        aria-label="Send"
      >
        <ArrowUp className="h-4 w-4" />
      </Button>
    </form>
  );
}
