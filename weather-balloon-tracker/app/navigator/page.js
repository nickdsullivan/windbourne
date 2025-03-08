"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";

export default function NavigatorPage() {
    return (
        <Suspense fallback={<div>Loading...</div>}>
            <NavigatorContent />
        </Suspense>
    );
}

function NavigatorContent() {
    const searchParams = useSearchParams();
    const balloonId = searchParams.get("balloonId");
    const [mapImageUrl, setMapImageUrl] = useState(null);
    const [balloonPosition, setBalloonPosition] = useState({ lat: -1, long: -1, alt: -1, speed: -1, bearing: -1 });
    const [targetPosition, setTargetPosition] = useState({ lat: 0, long: 0, alt: balloonPosition.alt ?? -1 });
    const [maxIters, setMaxIters] = useState(20);
    const [directions, setDirections] = useState(null);
    const [isNavigating, setIsNavigating] = useState(false);
    const [displayedImageSize, setDisplayedImageSize] = useState({ width: 750, height: 750 });
    const [originalImageSize] = useState({ width: 1280, height: 1275 });
    const [hasDirections, setHasDirections] = useState(false);

    const imgRef = useRef(null);



    useEffect(() => {
        const url = `http://localhost:8000/get-directions-map?balloon_id=${balloonId}&hour=0&x=${targetPosition.lat}&y=${targetPosition.long}`
        if (!hasDirections) {
            url = `http://localhost:8000/single-balloon-map-navigator?balloon_id=${balloonId}&hour=0&x=${targetPosition.lat}&y=${targetPosition.long}`
        }
        fetch(url, {
            method: 'GET',
            headers: {
                'ngrok-skip-browser-warning': 'true',
            },
        })

            .then((response) => response.blob())
            .then((blob) => {
                const imageObjectUrl = URL.createObjectURL(blob);
                setMapImageUrl(imageObjectUrl);
            })
            .catch((error) => console.error("Error fetching image:", error));
    }, [selectedHour]); // Re-fetch image when `selectedHour` changes
    useEffect(() => {
        fetch(`https://dear-jolly-sunbeam.ngrok-free.app/balloon-details?balloon_id=${balloonId}&hour=0`, {
            method: 'GET',
            headers: {
                'ngrok-skip-browser-warning': 'true'
            }
        })
            .then((res) => res.json())
            .then((data) => {
                setBalloonPosition(data);
                updateImageSize();
            })
            .catch((error) => console.error("Error fetching positions:", error));
    }, [balloonId]);

    const updateImageSize = () => {
        if (imgRef.current) {
            setDisplayedImageSize({
                width: imgRef.current.clientWidth,
                height: imgRef.current.clientHeight,
            });
        }
    };

    const handleImageLoad = () => {
        updateImageSize();
    };

    const handleImageClick = (event) => {
        if (!imgRef.current) return;
        updateImageSize();
        setHasDirections(false);

        // Click coordinates within the displayed image
        const rect = imgRef.current.getBoundingClientRect();
        const clickX_displayed = event.clientX - rect.left;
        const clickY_displayed = event.clientY - rect.top;

        // Convert from displayed coords => original coords
        const zoom = Math.log2(originalImageSize.width / 256);
        const clickX_original = (clickX_displayed / displayedImageSize.width) * originalImageSize.width;
        const clickY_original = (clickY_displayed / displayedImageSize.height) * originalImageSize.height;
        const { lat, long } = loc2pixels(clickX_original, clickY_original, zoom);
        setTargetPosition({ lat: lat, long: long, alt: balloonPosition.alt });
    };

    const handleNavigationClick = () => {
        setIsNavigating(true);
        console.log(balloonPosition);
        console.log(targetPosition);
        console.log(maxIters);

        fetch(`https://dear-jolly-sunbeam.ngrok-free.app/start-navigation?lat=${balloonPosition.lat}&long=${balloonPosition.long}&alt=${balloonPosition.alt}&t_lat=${targetPosition.lat}&t_long=${targetPosition.long}&t_alt=${targetPosition.alt}&max_iters=${maxIters}`, {
            method: 'GET',
            headers: {
                'ngrok-skip-browser-warning': 'true'
            }
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Failed to get path");
                }
                return response.json();
            })
            .then((data) => {
                setDirections(data);
                console.log("Got path!", data);
            })
            .catch((err) => {
                console.error("Error refreshing data:", err);
            })
            .finally(() => {
                setHasDirections(true);
                setIsNavigating(false);
            });
    };

    function loc2pixels(x, y, zoom) {
        const mapSize = 256 * Math.pow(2, zoom);
        const longitude = (x / mapSize) * 360 - 180;
        const latRad = Math.PI - (2 * Math.PI * y) / mapSize;
        const latitude = (180 / Math.PI) * Math.atan(Math.sinh(latRad));

        return { lat: latitude, long: longitude };
    }

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setTargetPosition((prev) => ({
            ...prev,
            [name]: value !== "" ? Number(value) : 0,
        }));
    };

    const handleMaxItersInputChange = (e) => {
        setMaxIters(e.target.value);
    };

    return (

        <main style={{ textAlign: "center", marginTop: "50px" }}>
            <h1>Navigate balloon #{balloonId} </h1>
            <p>Click a spot on the map and press navigate #{balloonId}.  </p>
            <p>With Max iteration 100 it will roughly take up to 5 minutes to process</p>
            <>
                <p>
                    <strong>Latitude:</strong> {balloonPosition.lat?.toFixed(2) ?? "N/A"}
                    <strong> Longitude:</strong> {balloonPosition.long?.toFixed(2) ?? "N/A"}
                    <strong> Altitude:</strong> {balloonPosition.alt?.toFixed(2) ?? "N/A"} km
                    <strong> Speed:</strong> {balloonPosition.speed?.toFixed(0) ?? "N/A"} km/h
                    <strong> Bearing:</strong> {balloonPosition.bearing?.toFixed(0) ?? "N/A"}°
                </p>
            </>
            <div>
                <h3>Target Location </h3>

                <label>
                    Latitude:
                    <input
                        type="number"
                        name="lat"
                        value={targetPosition.lat}
                        onChange={handleInputChange}
                        style={{ marginLeft: "10px", marginRight: "10px", padding: "5px", width: "100px" }}
                    />
                </label>
                <label>
                    Longitude:
                    <input
                        type="number"
                        name="long"
                        value={targetPosition.long}
                        onChange={handleInputChange}
                        style={{ marginLeft: "10px", marginRight: "10px", padding: "5px", width: "100px" }}
                    />
                </label>
                <label>
                    Maximium iteration:
                    <input
                        type="number"
                        name="maxIters"
                        value={maxIters}
                        onChange={handleMaxItersInputChange}
                        style={{ marginLeft: "10px", marginRight: "10px", padding: "5px", width: "100px" }}
                    />
                </label>

            </div>
            <button onClick={handleNavigationClick} disabled={isNavigating}>
                {isNavigating ? "Finding Path" : "Click to find path"}
            </button>

            {balloonPosition ? (
                <div
                    style={{
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "flex-start",
                        gap: "1rem", // spacing between the three boxes
                    }}
                >

                    <div
                        style={{
                            display: "flex",
                            justifyContent: "center",
                            alignItems: "flex-start",
                            gap: "1rem", // spacing between the boxes
                        }}
                    >
                        <div style={{ position: "relative", display: "inline-block" }}>
                            {/* Use updated map URL after directions are calculated */}
                            <img
                                ref={imgRef}
                                src={mapImageUrl}
                                alt="Balloon Navigation Map"
                                onLoad={handleImageLoad}
                                onClick={handleImageClick}
                                style={{
                                    width: "100%", // or any size you prefer
                                    height: "auto",
                                    cursor: "pointer",
                                    display: "block",
                                }}
                            />
                        </div>
                    </div>
                </div>

            ) : (
                <p>Loading balloon position...</p>
            )}
            {hasDirections ? (
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",  // Stack items vertically
                        justifyContent: "center",
                        alignItems: "flex-start",
                        gap: "1rem",  // spacing between the rows
                        border: "2px solid #000",  // Add a border around the box
                        padding: "1rem",  // Padding inside the box
                        borderRadius: "8px",  // Optional: rounded corners
                    }}
                >
                    <h3>Directions</h3>
                    {directions.map((direction, index) => (
                        <div key={index} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                            <p>
                                ({direction.time}):
                                <strong> Go to Altitude:</strong> {direction.alt.toFixed(2)} km for 1 hour |
                                <strong> Current Location:</strong> {direction.lat.toFixed(2)}, {direction.long.toFixed(2)} |
                                <strong> Wind Speed:</strong> {direction.speed.toFixed(0)} km/h |
                                <strong> Wind Bearing:</strong> {direction.bearing.toFixed(0)} |
                                <strong> Distance:</strong> {direction.distance.toFixed(2)} |
                            </p>
                        </div>
                    ))}
                    <p><strong>You have reached your destination</strong></p>
                </div>
            ) : (
                <p>No directions</p>
            )}

        </main>
    );
}
