"use client";

import React, { useState, useRef, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://shxz7-ml-task.hf.space";

// Renders a message string with **bold** markers and newlines into React elements
function renderMessageText(text) {
  return text.split("\n").map((line, li) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={li}>
        {parts.map((part, pi) => {
          if (part.startsWith("**") && part.endsWith("**")) {
            return <strong key={pi}>{part.slice(2, -2)}</strong>;
          }
          return part;
        })}
        {li < text.split("\n").length - 1 && <br />}
      </span>
    );
  });
}

export default function ChatInterface({ onLoadOutfitInCanvas }) {
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hello! I am AURA, your personal AI Fashion Stylist. Tell me about the look you are searching for today! For example, you can ask:\n\n• 'I need a smart casual outfit for an office meeting'\n• 'Show me a black cocktail dress outfit for a party'\n• 'What should I wear to a summer wedding for men?'"
    }
  ]);
  const [inputVal, setInputVal] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputVal.trim() || loading) return;

    const userMessageText = inputVal;
    setInputVal("");
    
    // Add user message to thread
    setMessages((prev) => [...prev, { sender: "user", text: userMessageText }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessageText })
      });

      if (!res.ok) {
        let errMsg = `Stylist is temporarily unavailable: ${res.statusText}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            errMsg = errData.detail;
          }
        } catch (_) {}
        
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: `⚠️ ${errMsg}`
          }
        ]);
        setLoading(false);
        return;
      }

      const recommendation = await res.json();

      // If the backend returned an error (catalog mismatch, off-topic, etc.) show it cleanly
      if (recommendation.error) {
        setMessages((prev) => [
          ...prev,
          {
            sender: "bot",
            text: recommendation.error,
            isError: true
          }
        ]);
        setLoading(false);
        return;
      }

      // Add bot response with recommendation details
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: recommendation.stylist_rationale || "I compiled this outfit for you:",
          recommendation: recommendation
        }
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `⚠️ Sorry, I encountered an issue: ${err.message}. Please try again.`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel chat-window">
      <div className="chat-header">
        <div className="stylist-avatar">A</div>
        <div className="stylist-name-box">
          <h3>AURA Stylist</h3>
          <div className="stylist-status">
            <span className="status-dot online" />
            <span>Online styling assistant</span>
          </div>
        </div>
      </div>

      <div className="chat-messages-container">
        {messages.map((msg, index) => {
          const isUser = msg.sender === "user";
          return (
            <div key={index} className={`message-row ${isUser ? "user-row" : "stylist-row"}`}>
              <div
                className={`msg-bubble ${msg.isError ? "error-bubble" : ""}`}
                style={{ whiteSpace: "pre-line" }}
              >
                {renderMessageText(msg.text)}

                {/* Embed recommendation panel if available */}
                {msg.recommendation && (
                  <div className="chat-outfit-recommendation">
                    <div className="chat-outfit-header">
                      <span className="chat-outfit-theme">
                        👔 {msg.recommendation.theme}
                      </span>
                      <span className={`outfit-badge ${msg.recommendation.source.toLowerCase()}`} style={{ fontSize: "0.6rem" }}>
                        {msg.recommendation.source.toLowerCase() === "curated" ? "Lookbook" : "AI Filtered"}
                      </span>
                    </div>

                    <div className="chat-outfit-items-list">
                      {Object.entries(msg.recommendation.items || {}).map(([role, item]) => (
                        <div key={item.id} className="chat-outfit-item-card">
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={`${API_BASE}/${item.image_path}`}
                            alt={item.name}
                            className="chat-item-img"
                            onError={(e) => {
                              e.target.src = "/fallback-product.jpg";
                            }}
                          />
                          <span className="chat-item-role">{role}</span>
                        </div>
                      ))}
                    </div>

                    <div className="chat-outfit-actions">
                      <span className="chat-outfit-price">
                        Total: ₹{msg.recommendation.total_price_inr}
                      </span>

                      {msg.recommendation.items?.hero && (
                        <button
                          className="canvas-load-btn"
                          onClick={() => onLoadOutfitInCanvas(msg.recommendation.items.hero, msg.recommendation)}
                        >
                          Load in Canvas
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {loading && (
          <div className="message-row stylist-row">
            <div className="msg-bubble typing-bubble">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} className="chat-input-area">
        <input
          type="text"
          placeholder="Ask AURA to style you..."
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="glow-btn send-msg-btn" disabled={loading || !inputVal.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
