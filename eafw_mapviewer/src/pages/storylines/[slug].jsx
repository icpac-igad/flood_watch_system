/**
 * Individual Storyline Viewer Page
 * Renders scrollytelling experience for a specific flood event
 */
import React, { useState, useEffect } from "react";
import FullscreenLayout from "@/wrappers/fullscreen";
import StorylineViewer from "@/components/storylines/viewer";

const StorylineDetailPage = () => {
  const [slug, setSlug] = useState(null);

  useEffect(() => {
    // Extract slug from URL path: /storylines/<slug>/
    const parts = window.location.pathname.split("/").filter(Boolean);
    const idx = parts.indexOf("storylines");
    if (idx >= 0 && parts[idx + 1]) {
      setSlug(parts[idx + 1]);
    }
  }, []);

  return (
    <FullscreenLayout
      title="Storyline | East Africa Flood Watch"
      description="Interactive flood event narrative"
    >
      {slug && <StorylineViewer slug={slug} />}
    </FullscreenLayout>
  );
};

export default StorylineDetailPage;
