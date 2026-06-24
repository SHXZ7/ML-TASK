"use client";

import React, { useState, useEffect } from "react";

const API_BASE = "http://127.0.0.1:8000";

// Helper to map color families to hex values for product catalog dots
const getColorFamilyHex = (color) => {
  const mapping = {
    black: "#000000",
    white: "#ffffff",
    grey: "#808080",
    gray: "#808080",
    blue: "#3b82f6",
    denim: "#1e3a8a",
    navy: "#0a192f",
    red: "#ef4444",
    green: "#10b981",
    yellow: "#f59e0b",
    pink: "#ec4899",
    purple: "#8b5cf6",
    orange: "#f97316",
    brown: "#78350f",
    beige: "#f5f5dc",
    gold: "#d97706",
    cream: "#fef3c7",
    tan: "#d2b48c",
    khaki: "#c3b091",
    silver: "#c0c0c0",
    peach: "#ffdab9",
    olive: "#808000",
    maroon: "#800000",
    rust: "#b45309",
    mustard: "#eab308"
  };
  
  const key = color ? color.toLowerCase().trim() : "";
  return mapping[key] || "#8c8c8c"; // default grey
};

export default function ProductCatalog({ onSelectProduct, activeProductId }) {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters State
  const [searchQuery, setSearchQuery] = useState("");
  const [genderFilter, setGenderFilter] = useState("all");
  const [occasionFilter, setOccasionFilter] = useState("all");

  useEffect(() => {
    async function fetchProducts() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE}/api/products`);
        if (!res.ok) {
          throw new Error(`Failed to load products: ${res.statusText}`);
        }
        const data = await res.json();
        setProducts(data);
        setFilteredProducts(data);
      } catch (err) {
        console.error("Error fetching products:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchProducts();
  }, []);

  // Filter Logic
  useEffect(() => {
    let result = products;

    if (genderFilter !== "all") {
      result = result.filter(
        (p) => p.gender.toLowerCase() === genderFilter.toLowerCase()
      );
    }

    if (occasionFilter !== "all") {
      result = result.filter(
        (p) => p.occasion.toLowerCase() === occasionFilter.toLowerCase()
      );
    }

    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.brand.toLowerCase().includes(q) ||
          p.category_label.toLowerCase().includes(q) ||
          p.tags.some((t) => t.toLowerCase().includes(q))
      );
    }

    setFilteredProducts(result);
  }, [searchQuery, genderFilter, occasionFilter, products]);

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
        <p>⚠️ Error loading catalog: {error}</p>
        <button 
          onClick={() => window.location.reload()} 
          className="glow-btn" 
          style={{ marginTop: "1rem", padding: "0.5rem 1rem" }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="catalog-container">
      <div className="catalog-header">
        <div className="catalog-title-area">
          <h2>Product Catalog</h2>
          <p>Browse {products.length} premium pieces in the collection</p>
        </div>
        
        <div className="search-bar">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            placeholder="Search brand, style, tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Filter Chips */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {/* Gender Filter */}
        <div className="filter-group">
          {["all", "men", "women"].map((gender) => (
            <button
              key={gender}
              className={`filter-chip ${genderFilter === gender ? "active" : ""}`}
              onClick={() => setGenderFilter(gender)}
            >
              {gender.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Occasion Filter */}
        <div className="filter-group">
          {["all", "casual", "office", "party", "wedding", "vacation", "festive", "sports"].map((occ) => (
            <button
              key={occ}
              className={`filter-chip ${occasionFilter === occ ? "active" : ""}`}
              onClick={() => setOccasionFilter(occ)}
            >
              {occ.charAt(0).toUpperCase() + occ.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="products-grid">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="catalog-skeleton" />
          ))}
        </div>
      ) : filteredProducts.length === 0 ? (
        <div className="glass-panel" style={{ padding: "4rem", textAlign: "center", color: "var(--muted)" }}>
          <p>No products match your current filters.</p>
        </div>
      ) : (
        <div className="products-grid">
          {filteredProducts.map((product) => {
            const isActive = activeProductId === product.id;
            const imgUrl = `${API_BASE}/${product.image_path}`;
            const dotColor = getColorFamilyHex(product.color_family);
            
            return (
              <div
                key={product.id}
                className="product-card glass-panel"
                style={isActive ? { borderColor: "var(--primary)", boxShadow: "0 0 15px rgba(139, 92, 246, 0.25)" } : {}}
                onClick={() => onSelectProduct(product)}
              >
                <div className="image-container">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={imgUrl}
                    alt={product.name}
                    className="product-img"
                    onError={(e) => {
                      e.target.src = "/fallback-product.jpg";
                    }}
                  />
                  <div className="product-badge">{product.occasion}</div>
                </div>
                
                <div className="product-details">
                  <span className="product-brand">{product.brand}</span>
                  <h3 className="product-title" title={product.name}>
                    {product.name}
                  </h3>
                  
                  <div className="product-footer">
                    <span className="product-price">₹{product.price_inr}</span>
                    <div className="color-dot-container">
                      <span 
                        className="color-dot" 
                        style={{ backgroundColor: dotColor }}
                        title={`Color: ${product.raw_color} (${product.color_family})`}
                      />
                      {product.rating && (
                        <span className="product-rating">
                          ★ {product.rating.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
