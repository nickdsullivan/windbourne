"use client"; // Needed for React hooks in Next.js
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
export default function Home() {

  const [refreshTime, setRefreshTime] = useState(null);
  const [selectedHour, setSelectedHour] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [windColumn, getWindColumn] = useState(false);
  // Store the balloon positions, each assumed to have { id, x, y } in ORIGINAL coords
  const [balloonPositions, setBalloonPositions] = useState([]);
  const [realBalloonPositions, setRealBalloonPositions] = useState([]);
  // Keep track of which balloon is selected
  const [selectedBalloon, setSelectedBalloon] = useState(null);
  // The original (full) image dimensions
  const [originalImageSize] = useState({ width: 1280, height: 1275 });
  // The actual rendered (on-screen) size of the <img>
  const [displayedImageSize, setDisplayedImageSize] = useState({ width: 0, height: 0 });
  useEffect(() => {
    fetchRefreshTime(); // Get the latest refresh time on page load
    updateImageSize();

    const checkRefresh = () => {
      if (refreshTime) {
        const now = new Date(); // Current local time
        const diffInMs = now - refreshTime;
        const diffInHours = diffInMs / (1000 * 60 * 60); // Convert ms to hours

        if (diffInHours > 1) {
          console.log("Last refresh was more than 1 hour ago. Refreshing...");
          handleRefreshClick();
        }
      }
    };

    // Run check on page load and every 1 minute
    const interval = setInterval(checkRefresh, 60 * 1000);
    return () => clearInterval(interval); // Cleanup on unmount
  }, [refreshTime]); // Re-run when refreshTime updates



  const handleRefreshClick = () => {
    setIsRefreshing(true);

    fetch("http://localhost:8000/refresh-data")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to refresh data");
        }
        return response.json();
      })
      .then((data) => {
        console.log("Data refresh successful:", data);
        fetchRefreshTime(); // Update last refresh time
      })
      .catch((err) => {
        console.error("Error refreshing data:", err);
      })
      .finally(() => {
        setIsRefreshing(false);
      });
  };

  // Function to fetch the latest refresh time
  const fetchRefreshTime = () => {
    fetch("http://localhost:8000/get-refresh-time")
      .then((response) => response.json())
      .then((data) => {
        // Convert UTC to local time
        const utcDate = new Date(data.time_utc + "Z");
        const localTime = utcDate.toLocaleString();
        setRefreshTime(localTime);
      })
      .catch((error) => console.error("Error fetching refresh time:", error));
  };
  // A ref for the <img> element so we can measure its size
  const imgRef = useRef(null);


  const updateImageSize = () => {
    if (imgRef.current) {
      setDisplayedImageSize({
        width: imgRef.current.clientWidth,
        height: imgRef.current.clientHeight,
      });
    }
  };


  useEffect(() => {
    fetch(`http://localhost:8000/get-positions?hour=${selectedHour}`)
      .then((res) => res.json())
      .then((data) => setBalloonPositions(data))
      .catch((error) => console.error("Error fetching positions:", error));
  }, [selectedHour]);



  useEffect(() => {
    window.addEventListener("resize", updateImageSize);
    return () => window.removeEventListener("resize", updateImageSize);
  }, []);

  const handleImageLoad = () => {
    updateImageSize();
  };

  const handleImageClick = (event) => {
    if (!imgRef.current) return;

    // Click coordinates within the displayed image
    const rect = imgRef.current.getBoundingClientRect();
    const clickX_displayed = event.clientX - rect.left;
    const clickY_displayed = event.clientY - rect.top;

    // Convert from displayed coords => original coords
    const clickX_original = (clickX_displayed / displayedImageSize.width) * originalImageSize.width;
    const clickY_original = (clickY_displayed / displayedImageSize.height) * originalImageSize.height;

    console.log("Clicked displayed coords:", clickX_displayed, clickY_displayed);
    console.log("Converted original coords:", clickX_original, clickY_original);

    // Find the nearest balloon in original space
    let nearestBalloon = null;
    let minDistance = Infinity;
    // A radius in "original" pixels
    const CLICK_RADIUS_ORIG = 80;

    balloonPositions.forEach((balloon) => {
      // balloon.x, balloon.y are in original coordinates
      const distance = Math.sqrt(
        (balloon.x - clickX_original) ** 2 +
        (balloon.y - clickY_original) ** 2
      );
      if (distance < minDistance) {
        minDistance = distance;
        nearestBalloon = balloon;
      }
    });

    // If within the CLICK_RADIUS_ORIG in original space, select the balloon
    if (nearestBalloon && minDistance <= CLICK_RADIUS_ORIG) {
      setSelectedBalloon(nearestBalloon);
      console.log(`Selected balloon #${nearestBalloon.id} at (${nearestBalloon.x},${nearestBalloon.y})`);
    } else {
      setSelectedBalloon(null);
      console.log("No balloon selected, click was too far.");
    }
  };

  return (
    <main style={{ textAlign: "center", marginTop: "50px" }}>
      <div>
        <h1>Weather Balloon Tracker 🎈 {isRefreshing}</h1>

        {/* Button and text above the map */}
        <div style={{ marginBottom: "20px" }}>
          <p>
            Click a balloon to select it. Selected Balloon:{" "}
            {selectedBalloon ? `#${selectedBalloon.id}` : "None"}
          </p>
          <p>
            Last Refreshed : {refreshTime}
          </p>
          <button onClick={handleRefreshClick} disabled={isRefreshing}>
            {isRefreshing ? "Refreshing..." : "Refresh Data"}
          </button>

          <div style={{ textAlign: "center", marginTop: "20px" }}>
            <input
              type="range"
              min="0"
              max="23"
              value={selectedHour}
              onChange={(e) => setSelectedHour(parseInt(e.target.value, 10))}
              style={{ width: "80%" }}
            />
            <p>Showing balloon data for {selectedHour} hours ago</p>
          </div>
        </div>
      </div>

      {/*
        FLEX CONTAINER with three children:
          1) Left box (scrollable filler text)
          2) Map in the center
          3) Right box (balloon details & GIF)
      */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-start",
          gap: "1rem", // spacing between the three boxes
        }}
      >
        {/* LEFT: Scrollable box with filler text */}
        <div
          style={{
            width: "800px",       // or 300px, your choice
            height: "800px",      // fixed height for the scroll
            overflowY: "auto",    // scrollable
            border: "1px solid #ccc",
            padding: "rem",
            boxSizing: "border-box",
            textAlign: "left",
          }}
        >
          <h1>Description and project notes</h1>
          <h3>Overview</h3>
          <p>
            {/* Filler text for now */}
            The goal of this project is use the variation in the over different altitudes to control where the positions of balloons.
            To get the wind data I open meteo is used.  For the balloon data I use the data you provided.  I interpolate and exterpolate the missing data.
          </p>
          <h3>Usage</h3>
          <p>
            {/* Filler text for now */}
            Idk anymore
          </p>
          <h3>Usage</h3>
          <p>
            Cras at dui viverra, hendrerit metus eget, condimentum diam. Integer id orci
            id justo lobortis dignissim. Proin consequat odio ac vestibulum porttitor.
            Maecenas at efficitur purus. Nam blandit, sapien non convallis volutpat,
            orci ex suscipit mi, non suscipit lacus tellus scelerisque orci.
          </p>
          <p>
            Donec aliquet mauris quis velit suscipit, et rutrum sem cursus. Sed vitae
            imperdiet augue. Etiam blandit pharetra lorem, eu ornare ligula pretium ut.
          </p>
        </div>
        <div style={{ position: "relative", display: "inline-block" }}>
          <img
            ref={imgRef}
            src={`http://localhost:8000/balloon-map?hour=${selectedHour}`}
            alt="Weather Balloon Map"
            onLoad={handleImageLoad}
            onClick={handleImageClick}
            style={{
              width: "100%", // or any size you prefer
              height: "auto",
              cursor: "pointer",
              display: "block",
            }}
          />
          {selectedBalloon && (
            <div
              style={{
                position: "absolute",
                left: `${(selectedBalloon.x / originalImageSize.width) *
                  displayedImageSize.width
                  }px`,
                top: `${(selectedBalloon.y / originalImageSize.height) *
                  displayedImageSize.height
                  }px`,
                transform: "translate(-50%, -50%)",
                width: "28px",
                height: "28px",
                borderRadius: "50%",
                border: "3px solid red",
                backgroundColor: "rgba(255, 0, 0, 0.3)",
                pointerEvents: "none",
              }}
            />
          )}

        </div>
        {/* RIGHT: Balloon details and GIF */}
        <div
          style={{
            width: "800px",
            minHeight: "600px",
            border: "1px solid #ccc",
            padding: "1rem",
            boxSizing: "border-box",
            textAlign: "left",
          }}
        >
          {selectedBalloon ? (
            <>
              <h2>Balloon #{selectedBalloon.id} Details </h2>
              <p><strong>Latitude:</strong> {selectedBalloon.lat.toFixed(4) ?? `N/A`}</p>
              <p><strong>Longitude:</strong> {selectedBalloon.long.toFixed(4) ?? `N/A`},</p>
              <p><strong>Altitude:</strong> {selectedBalloon.alt.toFixed(4) ?? `N/A`} km</p>
              <p><strong>Speed:</strong> {selectedBalloon.speed.toFixed(2) ?? "N/A"} km/h </p>
              <p><strong>Bearing:</strong> {selectedBalloon.bearing.toFixed(2) ?? "N/A"}°</p>
              <div style={{ marginTop: "1rem", textAlign: "center" }}>
                <img
                  src={`http://localhost:8000/wind-column?balloon_id=${selectedBalloon.id}&hour=${selectedHour}`}
                  alt={`Wind Column for balloon #${selectedBalloon.id}`}
                  style={{
                    maxWidth: "100%",
                    height: "auto",
                    border: "1px solid #ccc",
                  }}
                />
              </div>
              {/* Pass balloonId as a query parameter */}
              <Link href={`/navigator?balloonId=${selectedBalloon.id}`}>
                <button>Navigate this Balloon #{selectedBalloon.id}</button>
              </Link>
            </>
          ) : (
            <p>Select a balloon to see its details.</p>
          )}


        </div>
      </div>
    </main>
  );
}  