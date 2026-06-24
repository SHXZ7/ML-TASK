"use client";

import React, { useState, useEffect } from "react";
import ChatInterface from "../components/ChatInterface";
import OutfitCanvas from "../components/OutfitCanvas";
import ProductCatalog from "../components/ProductCatalog";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://shxz7-ml-task.hf.space";

export default function Home() {
  const [activeTab, setActiveTab] = useState("chat"); // "chat" or "catalog"
  const [selectedHeroProduct, setSelectedHeroProduct] = useState(null);
  const [preloadedRecommendation, setPreloadedRecommendation] = useState(null);
  const [backendOnline, setBackendOnline] = useState(null);

  // Poll backend health status
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "healthy") {
            setBackendOnline(true);
            return;
          }
        }
        setBackendOnline(false);
      } catch (err) {
        setBackendOnline(false);
      }
    }

    checkHealth();
    // Re-check every 15 seconds
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLoadOutfitInCanvas = (product, recommendation = null) => {
    setSelectedHeroProduct(product);
    setPreloadedRecommendation(recommendation);
  };

  const handleSelectProductFromCatalog = (product) => {
    setSelectedHeroProduct(product);
    setPreloadedRecommendation(null); // force API query for new starting item
  };

  return (
    <div className="app-container">
      {/* Brand Header / Navbar */}
      <header className="app-header">
        <div className="brand-section">
          <span className="brand-logo gradient-text">AURA</span>
          <span className="brand-tagline">AI Fashion Stylist</span>
        </div>
        
        <div className="header-actions">
          {/* Tabs Navigation */}
          <nav className="tabs-navigation">
            <button
              className={`tab-button ${activeTab === "chat" ? "active" : ""}`}
              onClick={() => setActiveTab("chat")}
            >
              💬 AI Assistant Chat
            </button>
            <button
              className={`tab-button ${activeTab === "catalog" ? "active" : ""}`}
              onClick={() => setActiveTab("catalog")}
            >
              🛍️ Product Catalog
            </button>
          </nav>

          <div className="status-indicator">
            <span className={`status-dot ${backendOnline === true ? "online" : backendOnline === false ? "offline" : ""}`} />
            <span className="status-text">
              {backendOnline === true ? "Online" : backendOnline === false ? "Offline" : "Connecting..."}
            </span>
          </div>
        </div>
      </header>

      {/* Main Dashboard Layout */}
      <div className="dashboard-grid">
        {/* Left Workspace Panel */}
        <div className="left-panel">
          {activeTab === "chat" ? (
            <ChatInterface onLoadOutfitInCanvas={handleLoadOutfitInCanvas} />
          ) : (
            <ProductCatalog 
              onSelectProduct={handleSelectProductFromCatalog} 
              activeProductId={selectedHeroProduct?.id} 
            />
          )}
        </div>

        {/* Right Preview/Playground Canvas Panel */}
        <div className="right-panel">
          <OutfitCanvas 
            heroProduct={selectedHeroProduct} 
            preloadedRecommendation={preloadedRecommendation}
            onSelectProduct={handleSelectProductFromCatalog} 
          />
        </div>
      </div>
    </div>
  );
}
