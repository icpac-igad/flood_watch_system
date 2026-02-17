/**
 * Storylines Hub Page
 * Lists all published flood event storylines
 */
import React from "react";
import FullscreenLayout from "@/wrappers/fullscreen";
import StorylinesHub from "@/components/storylines/hub";

const StorylinesPage = () => {
  return (
    <FullscreenLayout
      title="Flood Event Storylines | East Africa Flood Watch"
      description="Interactive narratives documenting major flood events across East Africa"
    >
      <StorylinesHub />
    </FullscreenLayout>
  );
};

export default StorylinesPage;
