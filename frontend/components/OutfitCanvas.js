"use client";

import React, { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://shxz7-ml-task.hf.space";

// Helper to map color strings to CSS colors for the detailed palette chips
const getColorHex = (colorName) => {
  const mapping = {
    black: "#111111",
    white: "#f8fafc",
    grey: "#71717a",
    gray: "#71717a",
    blue: "#2563eb",
    denim: "#1e3a8a",
    navy: "#0f172a",
    red: "#ef4444",
    green: "#10b981",
    yellow: "#eab308",
    pink: "#ec4899",
    purple: "#8b5cf6",
    orange: "#f97316",
    brown: "#78350f",
    beige: "#e4e4e7",
    gold: "#d97706",
    cream: "#fef3c7",
    tan: "#d2b48c",
    khaki: "#c3b091",
    silver: "#94a3b8",
    peach: "#ffedd5",
    olive: "#4d7c0f",
    maroon: "#7f1d1d",
    rust: "#b45309",
    blush: "#fda4af",
    mustard: "#eab308",
    emerald: "#047857",
    burgundy: "#800020",
    lavender: "#e9d5ff",
    violet: "#7c3aed"
  };
  
  const key = colorName ? colorName.toLowerCase().trim() : "";
  return mapping[key] || "#71717a"; // fallback
};

export default function OutfitCanvas({ heroProduct, preloadedRecommendation, onSelectProduct }) {
  const [recommendation, setRecommendation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!heroProduct) {
      setRecommendation(null);
      return;
    }

    if (preloadedRecommendation) {
      setRecommendation(preloadedRecommendation);
      return;
    }

    async function fetchRecommendation() {
      try {
        setLoading(true);
        setError(null);
        const res = await fetch(`${API_BASE}/api/recommend/${heroProduct.id}`);
        if (!res.ok) {
          throw new Error(`Failed to load recommendations for product ${heroProduct.id}: ${res.statusText}`);
        }
        const data = await res.json();
        setRecommendation(data);
      } catch (err) {
        console.error("Error fetching recommendation:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchRecommendation();
  }, [heroProduct, preloadedRecommendation]);

  if (!heroProduct) {
    return (
      <div className="glass-panel canvas-empty">
        <div className="canvas-empty-icon">🧥</div>
        <h3>Select a Product to Style</h3>
        <p style={{ maxWidth: "340px", fontSize: "0.9rem" }}>
          Click on any item in the catalog browser or choose a look from the AI assistant to view compatible coordinates and styling rationales.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: "3rem", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ width: "150px", height: "24px", background: "rgba(255,255,255,0.05)", borderRadius: "4px", animation: "pulse 1.5s infinite" }} />
          <div style={{ width: "80px", height: "24px", background: "rgba(255,255,255,0.05)", borderRadius: "4px", animation: "pulse 1.5s infinite" }} />
        </div>
        <div style={{ height: "140px", background: "rgba(255,255,255,0.05)", borderRadius: "12px", animation: "pulse 1.5s infinite" }} />
        <div style={{ height: "180px", background: "rgba(255,255,255,0.05)", borderRadius: "12px", animation: "pulse 1.5s infinite" }} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
        <p>⚠️ Error compiling recommendation: {error}</p>
        <button 
          onClick={() => {
            // trigger refetch by forcing a state reset
            const temp = heroProduct;
            onSelectProduct(null);
            setTimeout(() => onSelectProduct(temp), 50);
          }}
          className="glow-btn" 
          style={{ marginTop: "1rem", padding: "0.5rem 1rem" }}
        >
          Retry
        </button>
      </div>
    );
  }

  if (!recommendation) return null;

  // Split palette colors
  const paletteColors = recommendation.palette 
    ? recommendation.palette.split("/").map(c => c.trim()).filter(Boolean)
    : [];

  const items = recommendation.items || {};
  const heroItem = items.hero || heroProduct;
  
  // Coordinated items are all items in the recommendation that are NOT the hero
  const coordinatedItems = Object.entries(items).filter(([role]) => role !== "hero");

  return (
    <div className="canvas-wrapper">
      <div className="canvas-header">
        <div className="canvas-title-area">
          <h2>Outfit Canvas</h2>
          <div className="canvas-subtitle" style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.25rem" }}>
            <span>Theme:</span>
            <strong style={{ color: "#fff" }}>{recommendation.theme}</strong>
          </div>
        </div>
        
        <span className={`outfit-badge ${recommendation.source.toLowerCase()}`}>
          {recommendation.source.toLowerCase() === "curated" ? "✨ Lookbook Curated" : "🤖 AI Vector Matched"}
        </span>
      </div>

      <div className="canvas-layout">
        <div className="canvas-items-flow">
          {/* Hero Spotlight */}
          <div className="glass-panel hero-spotlight">
            <span className="hero-badge-tag">Selected Hero</span>
            <div className="spotlight-img-box">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`${API_BASE}/${heroItem.image_path}`}
                alt={heroItem.name}
                style={{ width: "100%", height: "100%", objectFit: "cover" }}
              />
            </div>
            <div className="spotlight-info">
              <span className="product-brand" style={{ fontSize: "0.8rem" }}>{heroItem.brand}</span>
              <h3 style={{ fontSize: "1.15rem", fontWeight: "700", margin: "0.25rem 0 0.5rem 0", color: "#fff" }}>
                {heroItem.name}
              </h3>
              <div style={{ display: "flex", gap: "0.5rem", fontSize: "0.8rem", color: "var(--muted-light)", flexWrap: "wrap" }}>
                <span className="glass-panel" style={{ padding: "0.2rem 0.5rem", borderRadius: "4px", background: "rgba(255,255,255,0.03)" }}>
                  {heroItem.category_label}
                </span>
                <span className="glass-panel" style={{ padding: "0.2rem 0.5rem", borderRadius: "4px", background: "rgba(255,255,255,0.03)" }}>
                  {heroItem.color_family}
                </span>
              </div>
              <div style={{ marginTop: "0.75rem", fontSize: "1.1rem", fontWeight: "700", color: "#fff" }}>
                ₹{heroItem.price_inr}
              </div>
            </div>
          </div>

          {/* Completing Pieces Grid */}
          {coordinatedItems.length > 0 && (
            <div>
              <h4 className="section-label" style={{ marginBottom: "0.75rem" }}>Completing Pieces</h4>
              <div className="outfit-slots-grid">
                {coordinatedItems.map(([role, item]) => {
                  const imgUrl = `${API_BASE}/${item.image_path}`;
                  return (
                    <div 
                      key={item.id} 
                      className="glass-panel slot-card"
                      onClick={() => onSelectProduct(item)}
                      style={{ cursor: "pointer" }}
                      title="Click to set as Hero"
                    >
                      <div className="slot-role">{role}</div>
                      <div className="slot-img-box">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={imgUrl}
                          alt={item.name}
                          style={{ width: "100%", height: "100%", objectFit: "cover", position: "absolute", top: 0, left: 0 }}
                        />
                      </div>
                      <div className="slot-name">{item.name}</div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                        <span className="slot-price">₹{item.price_inr}</span>
                        <span 
                          style={{ 
                            width: "8px", 
                            height: "8px", 
                            borderRadius: "50%", 
                            backgroundColor: getColorHex(item.color_family),
                            border: "1px solid rgba(255,255,255,0.2)"
                          }} 
                          title={item.color_family}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="canvas-details-sidebar">
          {/* Color Palette Section */}
          {paletteColors.length > 0 && (
            <div className="glass-panel canvas-panel-section">
              <span className="section-label">Color Harmony</span>
              <div className="palette-chips" style={{ marginTop: "0.5rem" }}>
                {paletteColors.map((colorName, idx) => (
                  <div key={idx} className="color-chip-detailed">
                    <span 
                      className="color-chip-dot" 
                      style={{ backgroundColor: getColorHex(colorName) }} 
                    />
                    <span>{colorName}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stylist Rationale Section */}
          {recommendation.stylist_rationale && (
            <div className="glass-panel canvas-panel-section">
              <span className="section-label">Stylist Notes</span>
              <p className="rationale-text" style={{ marginTop: "0.5rem" }}>
                "{recommendation.stylist_rationale}"
              </p>
            </div>
          )}

          {/* Total Price Section */}
          <div className="glass-panel canvas-panel-section" style={{ marginTop: "auto" }}>
            <div className="total-price-box">
              <span className="section-label">Total Outfit Cost</span>
              <span className="total-price-val">₹{recommendation.total_price_inr}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
