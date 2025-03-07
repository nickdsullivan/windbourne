"use client";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, useRef } from "react";

export default function NavigatorPage() {
    const searchParams = useSearchParams();
    const balloonId = searchParams.get("balloonId");
    const [balloonPosition, setBalloonPosition] = useState({ lat: -1, long: -1, alt: -1, speed: -1, bearing: -1 });
    const [targetPosition, setTargetPosition] = useState({ lat: -1, long: -1, alt: -1 });
    const [hasDirections, setDirections] = useState(false);
    const [isNavigating, setIsNavigating] = useState(false);
    const [displayedImageSize, setDisplayedImageSize] = useState({ width: 750, height: 750 });
    const [originalImageSize] = useState({ width: 1280, height: 1275 });




    const imgRef = useRef(null);

    useEffect(() => {
        fetch(`http://localhost:8000/balloon-details?balloon_id=${balloonId}&hour=0`)
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
        console.log(displayedImageSize.width)
        // Click coordinates within the displayed image
        const rect = imgRef.current.getBoundingClientRect();
        const clickX_displayed = event.clientX - rect.left;
        const clickY_displayed = event.clientY - rect.top;

        // Convert from displayed coords => original coords
        const zoom = Math.log2(originalImageSize.width / 256);
        const clickX_original = (clickX_displayed / displayedImageSize.width) * originalImageSize.width;
        const clickY_original = (clickY_displayed / displayedImageSize.height) * originalImageSize.height;
        const { lat, long } = loc2pixels(clickX_original, clickY_original, zoom);
        setTargetPosition({ lat: lat, long: long, alt : balloonPosition.alt});


    };

    const handleNavigationClick = () => {
        setIsNavigating(true)

        fetch(`http://localhost:8000/start-navigation?lat=${balloonPosition.lat}&long=${balloonPosition.long}&alt=${balloonPosition.alt}&t_lat=${targetPosition.lat}&t_long=${targetPosition.long}&t_alt=${targetPosition.alt}`)
            .then((response) => {

                if (!response.ok) {
                    setDirections(false);
                    throw new Error("Failed to refresh data");
                }
                return response.json();
            })
            .then((data) => {
                setDirections(true);
                console.log("Data refresh successful:", data);
            })
            .catch((err) => {
                console.error("Error refreshing data:", err);
            })
            .finally(() => {
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
        setTargetPosition(prev => ({
            ...prev,
            [name]: value
        }));
    };

    return (

        <main style={{ textAlign: "center", marginTop: "50px" }}>
            <h1>Navigate balloon #{balloonId} </h1>
            <p>Click a spot on the map and press navigate #{balloonId} </p>
            <>
                <p>
                    <strong>Latitude:</strong> {balloonPosition.lat?.toFixed(4) ?? "N/A"}
                    <strong> Longitude:</strong> {balloonPosition.long?.toFixed(4) ?? "N/A"}
                    <strong> Altitude:</strong> {balloonPosition.alt?.toFixed(4) ?? "N/A"} km
                    <strong> Speed:</strong> {balloonPosition.speed?.toFixed(2) ?? "N/A"} km/h
                    <strong> Bearing:</strong> {balloonPosition.bearing?.toFixed(2) ?? "N/A"}°
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

            </div>
            <button onClick={handleNavigationClick} disabled={isNavigating}>
                {isNavigating ? "Finding Path" : "Finding Path"}
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
                    <div style={{ position: "relative", display: "inline-block" }}>
                        <img
                            ref={imgRef}
                            src={`http://localhost:8000/single-balloon-map-navigator?balloon_id=${balloonId}&hour=0&x=${targetPosition.lat}&y=${targetPosition.long}`}
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

                    </div>


                </div>

            ) : (
                <p>Loading balloon position...</p>
            )}
        </main>
    );
}
