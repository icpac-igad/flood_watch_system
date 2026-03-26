import layersIcon from "@/assets/icons/layers.svg?sprite";
import globeIcon from "@/assets/icons/globe.svg?sprite";
import searchIcon from "@/assets/icons/search.svg?sprite";
import analysisIcon from "@/assets/icons/analysis.svg?sprite";
import settingsIcon from "@/assets/icons/settings.svg?sprite";
import satelliteIcon from "@/assets/icons/satellite.svg?sprite";
import myAccountIcon from "@/assets/icons/myhw.svg?sprite";

import Analysis from "@/components/analysis";
import Legend from "@/components/map/components/legend";
import UtilityPanel from "@/components/utility-panel";
import Basemaps from "@/components/basemaps";
import Datasets from "./components/sections/datasets";
import Search from "./components/sections/search";
import MyAccount from "./components/sections/my-account";

export const mobileSections = [
  {
    label: "layers",
    slug: "datasets",
    icon: globeIcon,
    Component: Datasets,
  },
  {
    label: "legend",
    slug: "legend",
    icon: layersIcon,
    Component: Legend,
    embed: true,
  },
  {
    label: "analysis",
    slug: "analysis",
    icon: analysisIcon,
    Component: Analysis,
    embed: true,
  },
  {
    label: "filters",
    slug: "utility",
    icon: settingsIcon,
    Component: UtilityPanel,
    embed: true,
    hideHeader: true,
  },
  {
    label: "basemaps",
    slug: "basemaps",
    icon: satelliteIcon,
    Component: Basemaps,
    embed: true,
  },
  {
    label: "my Account",
    slug: "my-account",
    icon: myAccountIcon,
    Component: MyAccount,
  },
];

export const searchSections = [
  // {
  //   label: "search",
  //   slug: "search",
  //   icon: searchIcon,
  //   Component: Search,
  //   large: true,
  // },
  {
    label: "my Account",
    slug: "my-account",
    icon: myAccountIcon,
    Component: MyAccount,
  },
];
