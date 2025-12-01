import React, { useEffect, useState } from "react";

export default function TripMap() {
  console.log
  const [componentProps, setComponentProps] = useState(null);
  
  // Debug logging
  console.log("=== TripMap component loaded ===");
  console.log("Raw props received:", props);
  console.log("Props type:", typeof props);
  console.log("Props is array?", Array.isArray(props));
  
  // Extract data from props - try multiple methods
  useEffect(() => {
    console.log("=== TripMap Props Debug ===");
    console.log("Props object:", props);
    console.log("Props keys:", props ? Object.keys(props) : "no props");
    console.log("Full props JSON:", JSON.stringify(props, null, 2));
    
    let actualProps = null;
    
    // Method 1: Check if props have the expected data directly
    if (props && (props.cities || props.mapUrl || props.embedUrl)) {
      actualProps = {
        cities: Array.isArray(props.cities) ? props.cities : (props.cities || []),
        mapUrl: props.mapUrl || '',
        embedUrl: props.embedUrl || ''
      };
      console.log("✓ Found props directly:", actualProps);
    }
    // Method 2: Check if props is an array (sometimes Chainlit passes arrays)
    else if (Array.isArray(props) && props.length > 0) {
      console.log("Props is an array:", props);
      // Try to find an object in the array with our data
      const dataObj = props.find(p => p && (p.cities || p.mapUrl));
      if (dataObj) {
        actualProps = {
          cities: Array.isArray(dataObj.cities) ? dataObj.cities : [],
          mapUrl: dataObj.mapUrl || '',
          embedUrl: dataObj.embedUrl || ''
        };
        console.log("✓ Found props in array:", actualProps);
      }
    }
    // Method 3: Check all keys in props for nested data
    else if (props && typeof props === 'object') {
      for (const key in props) {
        const value = props[key];
        if (value && typeof value === 'object' && (value.cities || value.mapUrl)) {
          actualProps = {
            cities: Array.isArray(value.cities) ? value.cities : [],
            mapUrl: value.mapUrl || '',
            embedUrl: value.embedUrl || ''
          };
          console.log(`✓ Found props in key "${key}":`, actualProps);
          break;
        }
      }
    }
    
    if (actualProps) {
      setComponentProps(actualProps);
    } else {
      console.error("✗ Could not find props anywhere!");
      console.error("Full props:", JSON.stringify(props, null, 2));
      
      // Show error in UI with helpful message
      setComponentProps({
        error: true,
        message: "Could not load map data. Props are empty. Check console for details."
      });
    }
  }, [props]);
  
  // Show loading or error state
  if (!componentProps) {
    return (
      <div style={{ padding: "20px", border: "2px solid orange" }}>
        <p>Loading map data...</p>
        <p style={{ fontSize: "12px", color: "#666" }}>
          If this persists, props may not be available. Check console for details.
        </p>
      </div>
    );
  }
  
  // Handle error state
  if (componentProps.error) {
    return (
      <div style={{ padding: "20px", border: "2px solid red" }}>
        <p style={{ color: "red" }}>Error: {componentProps.message}</p>
        <p style={{ fontSize: "12px", color: "#666" }}>
          Please check the browser console for debugging information.
        </p>
      </div>
    );
  }
  
  const { cities = [], mapUrl, embedUrl } = componentProps;
  
  console.log("Parsed - cities:", cities, "mapUrl:", mapUrl, "embedUrl:", embedUrl);
  
  // Always render something to verify the component loads
  if (!cities || cities.length === 0) {
    return (
      <div style={{ padding: "20px", border: "2px solid orange" }}>
        <p>No cities to display</p>
        <p>Props: {JSON.stringify(props)}</p>
      </div>
    );
  }

  // Always use embedUrl for iframe
  console.log("Map source URL (embed):", embedUrl);
  console.log("Map source URL (regular):", mapUrl);

  // If no embed URL, try to construct one or show error
  if (!embedUrl) {
    console.warn("No embed URL available - this means Google Maps Embed API key might be missing or geocoding failed");
    return (
      <div style={{ width: "100%", padding: "16px" }}>
        <div style={{ marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>
            🗺️ Trip Map - {cities.length} cities
          </h3>
        </div>
        
        <div style={{ padding: "20px", border: "2px solid #ddd", borderRadius: "8px", textAlign: "center", backgroundColor: "#fff3cd" }}>
          <p style={{ marginBottom: "12px", color: "#856404" }}>
            ⚠️ Map embedding requires Google Maps Embed API key. Click below to view in Google Maps:
          </p>
          {mapUrl && (
            <a
              href={mapUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: "12px 24px",
                backgroundColor: "#1976d2",
                border: "none",
                borderRadius: "4px",
                textDecoration: "none",
                color: "white",
                fontSize: "16px",
                fontWeight: "500",
                display: "inline-block"
              }}
            >
              Open in Google Maps →
            </a>
          )}
          <p style={{ marginTop: "12px", fontSize: "14px", color: "#666" }}>
            <strong>Cities:</strong> {Array.isArray(cities) ? cities.join(", ") : String(cities)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", padding: "16px" }}>
      <div style={{ marginBottom: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "600" }}>
          🗺️ Trip Map - {cities.length} cities
        </h3>
        {mapUrl && (
          <a
            href={mapUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              padding: "8px 12px",
              backgroundColor: "transparent",
              border: "1px solid #ccc",
              borderRadius: "4px",
              textDecoration: "none",
              color: "#1976d2",
              fontSize: "14px"
            }}
          >
            Open in Google Maps →
          </a>
        )}
      </div>
      
      <div style={{ position: "relative", width: "100%", height: "400px", borderRadius: "8px", overflow: "hidden" }}>
        <iframe
          width="100%"
          height="100%"
          style={{
            border: 0,
            borderRadius: "8px",
          }}
          loading="lazy"
          allowFullScreen
          referrerPolicy="no-referrer-when-downgrade"
          src={embedUrl}
          title="Trip Map"
        />
      </div>
      
      <div style={{ marginTop: "12px", fontSize: "14px", color: "#666" }}>
        <strong>Cities:</strong> {Array.isArray(cities) ? cities.join(", ") : String(cities)}
      </div>
    </div>
  );
}
