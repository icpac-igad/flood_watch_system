import { useState, useEffect } from "react";
import { useDispatch } from "react-redux";

import useRouter from "@/utils/router";
import { decodeQueryParams } from "@/utils/url";

import FullscreenLayout from "@/wrappers/fullscreen";
import Map from "@/layouts/map";

import MapUrlProvider from "@/providers/map-url-provider";
import LocationProvider from "@/providers/location-provider";

import {
  setMapSettings,
  setFilterInteractions,
  setParamInteractions,
  setInitialParamInteractions,
  setCmsScopes,
} from "@/components/map/actions";
import { setMainMapSettings } from "@/layouts/map/actions";
import { setMenuSettings } from "@/components/map-menu/actions";
import { setAnalysisSettings } from "@/components/analysis/actions";
import { setModalMetaSettings } from "@/components/modals/meta/actions";
import { setMapPrompts } from "@/components/prompts/map-prompts/actions";

const notFoundProps = {
  error: 404,
  title: "Location Not Found",
  errorTitle: "Location Not Found",
};

const ALLOWED_TYPES = ["country", "use", "geostore", "aoi", "point"];

export const getServerSideProps = async ({ req, params }) => {
  const [type] = params?.location || [];

  if (type && !ALLOWED_TYPES.includes(type)) {
    return {
      props: notFoundProps,
    };
  }

  if (!type) {
    return {
      props: {
        title: "MapViewer",
        description: "MapViewer",
      },
    };
  }

  if (type === "country") {
    return {
      props: {
        title: "MapViewer For Country",
      },
    };
  }

  if (type === "aoi") {
    return {
      props: {
        title: "MapViewer for Area of Interest",
      },
    };
  }

  if (type === "point") {
    return {
      props: {
        title: "MapViewer for custom point",
      },
    };
  }

  if (type === "geostore") {
    return {
      props: {
        title: "MapViewer for custom area",
      },
    };
  }

  try {
    const title = "MapViewer";

    const description = "MapViewer";
    const noIndex = !["country"].includes(type);

    return {
      props: {
        title,
        description,
        noIndex,
      },
    };
  } catch (err) {
    return {
      props: notFoundProps,
    };
  }
};

const MapPage = (props) => {
  const dispatch = useDispatch();
  const [ready, setReady] = useState(false);
  const [locationReady, setLocationReady] = useState(false);
  const { query, asPath, isFallback } = useRouter();
  const fullPathname = asPath?.split("?")?.[0];

  useEffect(() => {
    const { map, mapData, mainMap, mapMenu, analysis, modalMeta, mapPrompts } =
      decodeQueryParams(query) || {};

    if (map) {
      dispatch(setMapSettings(map));
    }

    // Restore map.data fields using granular actions
    if (mapData?.filterInteractions) {
      dispatch(setFilterInteractions(mapData.filterInteractions));
    }

    if (mapData?.paramInteractions) {
      dispatch(setParamInteractions(mapData.paramInteractions));
    }

    if (mainMap) {
      dispatch(setMainMapSettings(mainMap));
    }

    if (mapMenu) {
      dispatch(setMenuSettings(mapMenu));
    }

    if (analysis) {
      dispatch(setAnalysisSettings(analysis));
    }

    if (modalMeta) {
      dispatch(setModalMetaSettings(modalMeta));
    }

    if (mapPrompts) {
      dispatch(setMapPrompts(mapPrompts));
    }
  }, [fullPathname, isFallback]);

  // Fetch CMS scopes and apply default scope on initial load
  useEffect(() => {
    const initCmsScopes = async () => {
      try {
        const res = await fetch('/api/v1/cms/scopes');
        if (!res.ok) return;
        const data = await res.json();

        // Store scopes in Redux for filter panel and other components
        dispatch(setCmsScopes(data));

        const defaultScope = data.default_scope || 'all';

        // Check if URL already provided scope params — don't override
        const decoded = decodeQueryParams(query) || {};
        const urlScope = query?.scope || decoded?.mapData?.paramInteractions?.scope;

        if (urlScope && urlScope !== 'all') {
          // URL provided a scope — use it and set as initial for "clear" behavior
          const scopeParams = {
            scope: urlScope,
            whca_filter: urlScope === 'whca',
          };
          dispatch(setParamInteractions(scopeParams));
          dispatch(setInitialParamInteractions(scopeParams));
        } else if (defaultScope !== 'all') {
          // No URL scope — apply CMS default
          const scopeParams = {
            scope: defaultScope,
            whca_filter: defaultScope === 'whca',
          };
          dispatch(setParamInteractions(scopeParams));
          dispatch(setInitialParamInteractions(scopeParams));
        }
      } catch (e) {
        // Silently fall back to 'all' on error
      }
    };
    initCmsScopes();
  }, []);

  // when setting the query params from the URL we need to make sure we don't render the map
  // on the server otherwise the DOM will be out of sync
  useEffect(() => {
    if (!ready) {
      setReady(true);
    }
  });

  const handleOnLocationReady = () => {
    setLocationReady(true);
  };

  return (
    <FullscreenLayout {...props}>
      {ready && (
        <>
          <LocationProvider onReady={handleOnLocationReady} />
          <MapUrlProvider />
          {locationReady && <Map />}
        </>
      )}
    </FullscreenLayout>
  );
};

export default MapPage;
