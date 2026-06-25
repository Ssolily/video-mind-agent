import { useState, useEffect } from "react";

const MOBILE_BREAKPOINT = 768;

export interface DeviceInfo {
  isMobile: boolean;
}

export function useDevice(): DeviceInfo {
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < MOBILE_BREAKPOINT);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  return { isMobile };
}
