"use client";

import { useState, useRef, useEffect } from "react";
import { authenticatedFetch } from "@/lib/auth";

/**
 * DFM Chat — Conversational Q&A panel for analysis results.
 *
 * Users can ask Gemini about violations, feature improvements,
 * and manufacturing best practices in the context of their analysis.
 */
export default function DfmChat({ analysisId, violations = [] }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const hasViolations = violations && violations.length > 0;

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Seed the chat with an initial greeting when opened for the first time
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const greeting = hasViolations
        ? `I've reviewed your analysis and found **${violations.length} DFM violation(s)**. Feel free to ask me about any of the issues detected — I can explain why they matter, suggest specific fixes, and recommend optimal parameter values for your material.`
        : "Your design looks great — no major DFM violations were detected! Feel free to ask me about any manufacturing best practices, feature optimizations, or general DFM guidelines.";

      setMessages([{ role: "assistant", content: greeting }]);
    }
  }, [isOpen]);

  async function sendMessage(e) {
    e?.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Build history for Gemini (exclude the initial greeting & current message)
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await authenticatedFetch(`/api/chat/${analysisId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          history: history,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to get response");
      }

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Sorry, I couldn't process that request. ${err.message || "Please try again."}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // Suggested questions based on violations
  const suggestedQuestions = hasViolations
    ? [
        "How do I fix the most critical violation?",
        "What are the ideal values for my material?",
        "Why does wall thickness matter in injection molding?",
      ]
    : [
        "How can I further optimize my design?",
        "What are DFM best practices for this material?",
        "How can I reduce manufacturing costs?",
      ];

  function handleSuggestionClick(question) {
    setInput(question);
    // Auto-send via a small timeout so the user sees the question appear
    setTimeout(() => {
      const userMsg = { role: "user", content: question };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      authenticatedFetch(`/api/chat/${analysisId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, history }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("Request failed");
          return res.json();
        })
        .then((data) => {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.response },
          ]);
        })
        .catch((err) => {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `⚠️ Sorry, something went wrong. ${err.message}`,
            },
          ]);
        })
        .finally(() => setLoading(false));
    }, 100);
  }

  // Simple markdown-like rendering: bold, bullet lists
  function renderMarkdown(text) {
    if (!text) return null;
    return text.split("\n").map((line, i) => {
      // Bold
      let rendered = line.replace(
        /\*\*(.*?)\*\*/g,
        '<strong class="text-slate-100">$1</strong>'
      );
      // Inline code
      rendered = rendered.replace(
        /`(.*?)`/g,
        '<code class="bg-slate-700/50 px-1 py-0.5 rounded text-brand-300 text-xs">$1</code>'
      );

      // Bullet points
      if (/^\s*[-*•]\s/.test(line)) {
        rendered = rendered.replace(/^\s*[-*•]\s/, "");
        return (
          <div key={i} className="flex items-start gap-2 ml-2 mb-1">
            <span className="text-brand-400 mt-1 flex-shrink-0 text-xs">●</span>
            <span
              className="text-sm text-slate-300 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: rendered }}
            />
          </div>
        );
      }

      // Numbered lists
      if (/^\s*\d+\.\s/.test(line)) {
        const numMatch = line.match(/^\s*(\d+)\.\s/);
        rendered = rendered.replace(/^\s*\d+\.\s/, "");
        return (
          <div key={i} className="flex items-start gap-2 ml-2 mb-1">
            <span className="text-brand-400 font-semibold text-xs mt-0.5 flex-shrink-0 w-4">
              {numMatch[1]}.
            </span>
            <span
              className="text-sm text-slate-300 leading-relaxed"
              dangerouslySetInnerHTML={{ __html: rendered }}
            />
          </div>
        );
      }

      // Empty lines = spacer
      if (!line.trim()) return <div key={i} className="h-2" />;

      return (
        <p
          key={i}
          className="text-sm text-slate-300 leading-relaxed mb-1"
          dangerouslySetInnerHTML={{ __html: rendered }}
        />
      );
    });
  }

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-2xl transition-all duration-300 ${
          isOpen
            ? "bg-slate-700 hover:bg-slate-600 rotate-0"
            : "bg-gradient-to-br from-brand-500 to-brand-600 hover:from-brand-400 hover:to-brand-500 shadow-brand-500/30"
        }`}
        id="dfm-chat-toggle"
        title={isOpen ? "Close chat" : "Ask about your analysis"}
      >
        {isOpen ? (
          <svg className="w-6 h-6 text-slate-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <>
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
            </svg>
            {/* Notification dot when there are violations */}
            {hasViolations && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-[10px] font-bold text-white animate-pulse">
                {violations.length}
              </span>
            )}
          </>
        )}
      </button>

      {/* Chat panel */}
      <div
        className={`fixed bottom-24 right-6 z-50 w-[420px] max-w-[calc(100vw-2rem)] transition-all duration-300 ease-out ${
          isOpen
            ? "opacity-100 translate-y-0 pointer-events-auto"
            : "opacity-0 translate-y-4 pointer-events-none"
        }`}
      >
        <div className="flex flex-col h-[560px] max-h-[calc(100vh-8rem)] rounded-2xl overflow-hidden border border-brand-500/20 shadow-2xl shadow-black/40"
          style={{ background: "rgba(8, 12, 28, 0.95)", backdropFilter: "blur(24px)" }}
        >
          {/* Header */}
          <div className="px-5 py-4 border-b border-slate-700/50 flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-100">DFM Assistant</h3>
                <p className="text-[11px] text-slate-500">Powered by Gemini AI • Ask about your analysis</p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4" id="dfm-chat-messages">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-brand-500/20 border border-brand-500/30 text-slate-200"
                      : "bg-slate-800/60 border border-slate-700/40"
                  }`}
                >
                  {msg.role === "assistant" ? (
                    <div className="space-y-1">{renderMarkdown(msg.content)}</div>
                  ) : (
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  )}
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-800/60 border border-slate-700/40 rounded-2xl px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-2 h-2 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span className="text-xs text-slate-500">Analyzing...</span>
                  </div>
                </div>
              </div>
            )}

            {/* Suggested questions - show only when no user messages sent yet */}
            {messages.length <= 1 && !loading && (
              <div className="space-y-2 pt-2">
                <p className="text-[11px] text-slate-500 uppercase tracking-wider font-medium px-1">
                  Suggested questions
                </p>
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSuggestionClick(q)}
                    className="w-full text-left text-sm text-slate-400 hover:text-slate-200 bg-slate-800/40 hover:bg-slate-700/50 border border-slate-700/30 hover:border-brand-500/30 rounded-xl px-3.5 py-2.5 transition-all duration-200"
                    id={`suggestion-${i}`}
                  >
                    <span className="text-brand-400 mr-2">→</span>
                    {q}
                  </button>
                ))}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <form
            onSubmit={sendMessage}
            className="flex-shrink-0 px-4 py-3 border-t border-slate-700/50"
          >
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about violations, fixes, or DFM tips..."
                disabled={loading}
                className="flex-1 bg-slate-800/60 border border-slate-700/40 rounded-xl px-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/30 transition-all disabled:opacity-50"
                id="dfm-chat-input"
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="w-10 h-10 rounded-xl bg-brand-500 hover:bg-brand-400 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center justify-center transition-all duration-200 flex-shrink-0"
                id="dfm-chat-send"
              >
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
