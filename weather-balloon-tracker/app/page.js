"use client"; // Needed for React hooks in Next.js

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
export default function Home() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_BACK_END_BASE_URL;
  const [mapImageUrl, setMapImageUrl] = useState(null);
  const [windGIFUrl, setWindGIFUrl] = useState(null);

  const [refreshTime, setRefreshTime] = useState(null);
  const [selectedHour, setSelectedHour] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [windColumn, setWindColumn] = useState(false);
  const [gettingWindColumn, setGettingWindColumn] = useState(false);

  // Store the balloon positions, each assumed to have { id, x, y } in ORIGINAL coords
  const [balloonPositions, setBalloonPositions] = useState([]);
  const [realBalloonPositions, setRealBalloonPositions] = useState([]);
  // Keep track of which balloon is selected
  const [selectedBalloon, setSelectedBalloon] = useState(null);
  // The original (full) image dimensions
  const [originalImageSize] = useState({ width: 1280, height: 1275 });
  // The actual rendered (on-screen) size of the <img>
  const [displayedImageSize, setDisplayedImageSize] = useState({ width: 0, height: 0 });



  const checkRefresh = () => {

    console.log(API_BASE_URL);
    console.log(refreshTime);
    if (refreshTime) {
      const now = new Date(); // Current local time
      const refreshTimeValue = new Date(refreshTime);
      const diffInMs = now - refreshTimeValue;
      const diffInHours = diffInMs / (1000 * 60 * 60); // Convert ms to hours
      console.log(diffInHours);

      if (diffInHours > 1) {
        console.log("Last refresh was more than 1 hour ago. Refreshing...");
        //handleRefreshClick();
      }
      else {
        console.log("No refresh");
      }
    }
  };

  useEffect(() => {
    fetch(`${API_BASE_URL}/balloon-map?hour=${selectedHour}`)
      .then((response) => response.blob())
      .then((blob) => {
        const imageObjectUrl = URL.createObjectURL(blob);
        setMapImageUrl(imageObjectUrl);
      })
      .catch((error) => console.error("Error fetching image:", error));
  }, [selectedHour]); // Re-fetch image when `selectedHour` changes


  // useEffect(() => {
  //   if (selectedBalloon) {
  //     setGettingWindColumn(true);
  //   }
  // }, [selectedHour, selectedBalloon?.id]);


  useEffect(() => {

    updateImageSize();
    fetchRefreshTime();


    // Run check on page load and every 1 minute
    const interval = setInterval(checkRefresh, 60 * 1000);
    return () => clearInterval(interval);
  }, [refreshTime]);



  const handleRefreshClick = () => {
    setIsRefreshing(true);

    fetch(`${API_BASE_URL}/refresh-data`)
      .then((response) => {
        if (!response.ok) {
          console.log(response);
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

  const handleWindColumnClick = () => {
    setGettingWindColumn(true);

    fetch(`${API_BASE_URL}/wind-column?balloon_id=${selectedBalloon.id}&hour=${selectedHour}`)
      .then((response) => response.blob())
      .then((blob) => {
        const gifObjectUrl = URL.createObjectURL(blob);
        setWindGIFUrl(gifObjectUrl);
        setGettingWindColumn(false);
        setWindColumn(true);
      })
      .catch((error) => console.error("Error fetching image:", error));
  };

  // Function to fetch the latest refresh time
  const fetchRefreshTime = () => {
    fetch(`${API_BASE_URL}/get-refresh-time`)
      .then((response) => response.json())
      .then((data) => {
        // Convert UTC to local time
        const utcDate = new Date(data.time_utc + "Z");
        const localTime = utcDate.toLocaleString();
        console.log(localTime);
        console.log(data.time_utc);
        setRefreshTime(localTime);
        checkRefresh();
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
    fetch(`${API_BASE_URL}/get-positions?hour=${selectedHour}`)
      .then((res) => res.json())
      .then((data) => {
        setBalloonPositions(data);
        balloonPositions.forEach((balloon) => {
          if (balloon.id == selectedBalloon.id) {
            setSelectedBalloon(balloon);
          }
        });

      })
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
            The goal of this project is to use variations in wind across different altitudes to control the positions of balloons.
            To get the wind data, I use Open-Meteo. For the balloon data, I use the data you provided. I interpolate and extrapolate the missing data.
          </p>
          <h3>Usage</h3>
          <p>
            You can skim through the last 23 hours of data using the slider above the map.
            Click on a balloon to view its location, elevation, speed, and bearing. The speed and bearing are calculated by taking the difference between its current location and its last recorded location.
            Click the button labeled <i>Update Wind Column</i>, and a GIF of the wind column will be generated.
            The black dot in the GIF represents the balloon&apos;s position.
            You can also click the button labeled <i>Navigate Balloon</i>, which will take you to the navigation page.
            On that page, click anywhere on the globe and press <i>Navigate</i>. I use beam search to predict future potential positions. You can adjust the parameters via the text boxes.
          </p>
          <h3>Notes</h3>
          <p>
            <strong>I only have 10,000 API calls for Open-Meteo per day.  If you navigate a balloon with a large beam width and a high number of maximum iterations, you will likely use all of them.</strong>
            The beam search treats locations as nodes and wind speed/direction as edges. I have limited the elevation to 10 possible heights to reduce the state space and minimize API calls.
            It is unlikely that the balloon will reach the target location exactly, as the wind is highly likely to blow it off track.
          </p>

          <p>
            The interpolation and extrapolation methods are fairly simple. The interpolation method takes the midpoint between two real data points.
            The extrapolation algorithm estimates the next location based on the past speed and bearing of the weather balloon.
          </p>

          <p>
            I also wrote a custom function to convert geographic coordinates to pixel values. The map uses a Web Mercator projection.
            Additionally, I implemented a custom function to calculate the distance and bearing between two latitude/longitude coordinates, as well as a function to determine a new latitude/longitude position based on a given distance and bearing.
          </p>
        </div>
        <div style={{ position: "relative", display: "inline-block" }}>
          <img
            ref={imgRef}
            src={mapImageUrl}
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
              <Link href={`/navigator?balloonId=${selectedBalloon.id}`}>
                <button>Navigate Balloon #{selectedBalloon.id}</button>
              </Link>
              <p><strong>Latitude:</strong> {selectedBalloon.lat.toFixed(3) ?? `N/A`}</p>
              <p><strong>Longitude:</strong> {selectedBalloon.long.toFixed(3) ?? `N/A`},</p>
              <p><strong>Altitude:</strong> {selectedBalloon.alt.toFixed(3) ?? `N/A`} km</p>
              <p><strong>Speed:</strong> {selectedBalloon.speed.toFixed(2) ?? "N/A"} km/h </p>
              <p><strong>Bearing:</strong> {selectedBalloon.bearing.toFixed(2) ?? "N/A"}°</p>
              <p><strong>Hour:</strong> {selectedBalloon.hour ?? "N/A"}°</p>
              <div style={{ marginTop: "1rem", textAlign: "center" }}>
                {windColumn ? (
                  <img
                    src={windGIFUrl}
                    alt={`Wind Column for balloon #${selectedBalloon.id}`}
                    style={{
                      maxWidth: "100%",
                      height: "auto",
                      border: "1px solid #ccc",
                    }}
                  />)
                  :
                  (
                    <p> </p>

                  )



                }
                <button onClick={handleWindColumnClick} disabled={gettingWindColumn}>
                  {gettingWindColumn ? "Loading" : "Update Wind Column"}
                </button>

              </div>
              {/* Pass balloonId as a query parameter */}
              <p> </p>
              <p> </p>
              <p> </p>


            </>
          ) : (
            <p>Select a balloon to see its details.</p>
          )}


        </div>
      </div>
    </main>
  );
}  
