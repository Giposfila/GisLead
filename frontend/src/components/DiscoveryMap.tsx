import { useEffect, useRef, useState } from "react";
import { ru } from "../i18n/ru";
import Icon from "./Icon";
import type { mountCity } from "./cityScene";

export default function DiscoveryMap() {
  const host = useRef<HTMLDivElement>(null);
  const controller = useRef<ReturnType<typeof mountCity>>();
  const [paused, setPaused] = useState(false);
  const [ready, setReady] = useState(false);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useEffect(() => {
    let cancelled = false;
    // The operational UI loads first; WebGL stays in a separate, optional chunk.
    import("./cityScene")
      .then(({ mountCity }) => {
        if (cancelled || !host.current) return;
        try {
          controller.current = mountCity(host.current);
          controller.current.setPaused(pausedRef.current);
          setReady(true);
        } catch {
          // The CSS map stays visible if WebGL is unavailable.
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      controller.current?.dispose();
      controller.current = undefined;
    };
  }, []);
  useEffect(() => {
    controller.current?.setPaused(paused);
  }, [paused]);

  return (
    <div className="discovery-map">
      <div className="city-scene" ref={host} aria-hidden="true" />
      <div className="map-fallback" aria-hidden="true">
        <div className="map-grid" />
        <div className="map-orbit orbit-one" />
        <div className="map-orbit orbit-two" />
        <div className="map-road road-one" />
        <div className="map-road road-two" />
        <span className="map-block block-one" />
        <span className="map-block block-two" />
        <span className="map-block block-three" />
        <span className="map-block block-four" />
        <span className="map-center">
          <Icon name="target" size={32} />
        </span>
      </div>
      <span className="map-source">
        2GIS <span>→</span> LeadGis
      </span>
      <span className="map-schematic">{ru.campaign.schematic}</span>
      <div className="map-bottom">
        <span className="map-live">
          <span className="status-dot" />
          {ru.campaign.mapLabel}
        </span>
        {ready && (
          <button
            type="button"
            className="map-motion"
            onClick={() => setPaused(!paused)}
            aria-label={
              paused ? ru.campaign.resumeMotion : ru.campaign.pauseMotion
            }
            aria-pressed={paused}
            title={paused ? ru.campaign.resumeMotion : ru.campaign.pauseMotion}
          >
            <Icon name={paused ? "play" : "pause"} size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
