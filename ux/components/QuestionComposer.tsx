"use client";

import { FormEvent, useState } from "react";
import { ArrowUp, BookOpen, ChevronDown, LoaderCircle, Paperclip, Sparkles } from "lucide-react";

export const SUGGESTIONS = [
  {
    short: "A species",
    prompt: "Where have lion-tailed macaques been recorded, and where did people actually look?",
  },
  {
    short: "The seasons",
    prompt: "Show how greenness moves through the year, including the cloudy-season gaps.",
  },
  {
    short: "Restoration",
    prompt: "What can the existing plots tell us about natural regeneration and what is still missing?",
  },
  {
    short: "The soundscape",
    prompt: "When is acoustic space most occupied, and what can we responsibly infer from that?",
  },
];

export function QuestionComposer({
  busy,
  onAsk,
  onPaper,
}: {
  busy: boolean;
  onAsk: (question: string) => void;
  onPaper: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [expanded, setExpanded] = useState(false);
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    onAsk(question.trim());
    setQuestion("");
    setExpanded(false);
  }
  if (!expanded) {
    return (
      <div className="ask-dock is-collapsed">
        <button className="ask-toggle" type="button" onClick={() => setExpanded(true)}>
          {busy ? <LoaderCircle className="spin" /> : <Sparkles />}
          <span>
            <strong>{busy ? "Reading the field index…" : "Ask this landscape"}</strong>
            <small>Request a map, comparison or paper method</small>
          </span>
          <ArrowUp />
        </button>
      </div>
    );
  }
  return (
    <div className="ask-dock">
      <div className="suggestion-row">
        <span>
          <Sparkles size={14} />
          Follow a thread
        </span>
        {SUGGESTIONS.map((suggestion) => (
          <button key={suggestion.short} type="button" onClick={() => onAsk(suggestion.prompt)}>
            {suggestion.short}
          </button>
        ))}
        <button
          className="collapse-dock"
          type="button"
          onClick={() => setExpanded(false)}
          aria-label="Minimise question box"
        >
          <ChevronDown size={14} />
        </button>
      </div>
      <form onSubmit={submit} className="ask-form">
        <button className="attach-button" type="button" onClick={onPaper} aria-label="Read a paper">
          <Paperclip size={19} />
        </button>
        <label>
          <span>Ask the landscape</span>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Where is there evidence—and where is there only silence?"
          />
        </label>
        <button className="send-button" type="submit" disabled={!question.trim() || busy}>
          {busy ? <LoaderCircle className="spin" size={20} /> : <ArrowUp size={20} />}
        </button>
      </form>
      <button className="paper-shortcut" type="button" onClick={onPaper}>
        <BookOpen size={15} />
        Recreate a paper method
      </button>
    </div>
  );
}
