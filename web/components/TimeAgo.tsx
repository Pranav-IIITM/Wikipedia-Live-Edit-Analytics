"use client";

import { useEffect, useState } from "react";

function relative(iso: string): string {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} h ago`;
  return `${Math.round(hours / 24)} days ago`;
}

/** Renders a fixed UTC time on the server, then a live relative time in the browser. */
export function TimeAgo({ iso }: { iso: string }) {
  const [text, setText] = useState<string | null>(null);
  useEffect(() => {
    const update = () => setText(relative(iso));
    update();
    const id = setInterval(update, 30_000);
    return () => clearInterval(id);
  }, [iso]);
  const utc = new Date(iso).toISOString().slice(11, 16) + " UTC";
  return <time dateTime={iso} title={utc}>{text ?? utc}</time>;
}
