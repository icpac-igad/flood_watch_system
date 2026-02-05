import React, { useState, useEffect } from 'react';
import { connect } from 'react-redux';
import { setDatasetParams } from '@/providers/datasets-provider/actions';
import {
  setMapSettings,
  setFilterInteractions,
  clearFilterInteractions,
  setParamInteractions,
  clearParamInteractions,
  setBoundaryData
} from '@/components/map/actions';
import { buildParamInteractionsFromBoundary } from '@/utils/params';
import { fetchAdminBoundaries } from '@/utils/boundary-utils';
import { selectBoundaryData } from '@/components/map/selectors';
import Dropdown from '@/components/ui/dropdown';

const selectInitialBbox = (state) => state.map?.data?.initialBbox || null;
const selectInitialParamInteractions = (state) => state.map?.data?.initialParamInteractions || null;
import '@/styles/filters.css';

const FilterItem = ({ label, onClear }) => (
  <div className="filter-item">
    <span>{label}</span>
    <button onClick={onClear} className="filter-clear">×</button>
  </div>
);

// Generic boundary selector component that follows DRY principle
const BoundarySelector = ({
  adminLevel,
  parentCode,
  selectedBoundary,
  placeholder,
  onChange,
  onClear,
  boundaryData,
  setBoundaryData,
  showOnlyIfParent = false,
  requestParams = {}
}) => {
  const [boundaries, setBoundaries] = useState([]);
  const requestParamsKey = JSON.stringify(requestParams || {});

  useEffect(() => {
    const loadBoundaries = async () => {
      if (showOnlyIfParent && !parentCode) {
        setBoundaries([]);
        return;
      }

      const data = await fetchAdminBoundaries(
        adminLevel,
        parentCode || '',
        true,
        { boundaryData, setBoundaryData, extraParams: requestParams }
      );
      setBoundaries(Array.isArray(data) ? data : []);
    };
    loadBoundaries();
  }, [adminLevel, parentCode, boundaryData, setBoundaryData, showOnlyIfParent, requestParamsKey]);

  // Defensive check to ensure boundaries is an array
  const availableBoundaries = Array.isArray(boundaries)
    ? boundaries.filter(boundary =>
        !selectedBoundary || boundary.code !== selectedBoundary.code
      )
    : [];

  if (showOnlyIfParent && !parentCode) return null;

  const dropdownOptions = [
    { label: placeholder, value: '' },
    ...availableBoundaries.map(boundary => ({
      label: boundary.name,
      value: boundary.code
    }))
  ];

  return (
    <div className="filter-container">
      {selectedBoundary && (
        <FilterItem
          label={selectedBoundary.name}
          onClear={onClear}
        />
      )}
      <Dropdown
        className="boundary-dropdown"
        theme="theme-dropdown-native"
        options={dropdownOptions}
        value=""
        onChange={(value) => {
          if (value) {
            const selected = boundaries.find(b => b.code === value);
            if (selected) {
              onChange(selected);
            }
          }
        }}
        native
      />
    </div>
  );
};

// Convenience wrappers for better readability
export const CountrySelector = (props) => (
  <BoundarySelector
    adminLevel={null}
    parentCode=""
    selectedBoundary={props.selectedCountry}
    placeholder="+ Select country"
    {...props}
  />
);

export const SubBorderSelector = ({ country, selectedSubBorder, parentCode, ...props }) => (
  <BoundarySelector
    adminLevel={0}
    parentCode={parentCode || country?.code}
    selectedBoundary={selectedSubBorder}
    placeholder="+ Select sub-border"
    showOnlyIfParent={true}
    {...props}
  />
);

export const LowerBorderSelector = ({ subBorder, selectedLowerBorder, parentCode, countryName, ...props }) => (
  <BoundarySelector
    adminLevel={1}
    parentCode={parentCode || subBorder?.code}
    selectedBoundary={selectedLowerBorder}
    placeholder="+ Select lower border"
    showOnlyIfParent={true}
    requestParams={countryName ? { country_id: countryName } : {}}
    {...props}
  />
);

// FilterPanelContainer configuration
const BOUNDARY_CONFIG = {
  country: {
    level: '0',
    borderLevel: '0',
    stateKey: 'selectedCountry',
    parentKey: null,
    nextLevel: 'subBorder'
  },
  subBorder: {
    level: '1',
    borderLevel: '1',
    stateKey: 'selectedSubBorder',
    parentKey: 'selectedCountry',
    nextLevel: 'lowerBorder'
  },
  lowerBorder: {
    level: '2',
    borderLevel: '2',
    stateKey: 'selectedLowerBorder',
    parentKey: 'selectedSubBorder',
    nextLevel: null
  }
};

class FilterPanelContainerComponent extends React.Component {
  handleBoundaryChange = async (boundaryType, boundary) => {
    const config = BOUNDARY_CONFIG[boundaryType];
    if (!config) return;

    const currentBoundary = this.props.filterInteractions[config.stateKey];
    if (currentBoundary?.code === boundary?.code) return;

    // Clear lower level boundaries
    const newFilterState = {};
    Object.keys(BOUNDARY_CONFIG).forEach(key => {
      if (this.shouldClearBoundary(key, boundaryType)) {
        newFilterState[BOUNDARY_CONFIG[key].stateKey] = null;
      }
    });

    newFilterState[config.stateKey] = boundary;

    // Update centralized filter state
    this.props.setFilterInteractions(newFilterState);

    // FloodWatch: Build parent boundaries object for spatial filtering
    const { selectedCountry, selectedSubBorder } = this.props.filterInteractions;
    const parentBoundaries = {
      country_name: boundaryType === 'country' ? boundary?.name : selectedCountry?.name || '',
      region_name: boundaryType === 'subBorder' ? boundary?.name :
                   (boundaryType === 'lowerBorder' ? selectedSubBorder?.name : ''),
    };

    // Update param interactions in Redux using consolidated utility
    const paramInteractions = buildParamInteractionsFromBoundary(
      boundary,
      config.level,
      config.borderLevel,
      'Admin',
      parentBoundaries
    );
    this.props.setParamInteractions(paramInteractions);

    if (boundary?.bbox) {
      await this.fitMapToBounds(boundary.bbox);
    }
  };

  clearBoundary = async (boundaryType) => {
    const config = BOUNDARY_CONFIG[boundaryType];
    if (!config) return;

    const newFilterState = {};
    Object.keys(BOUNDARY_CONFIG).forEach(key => {
      const keyConfig = BOUNDARY_CONFIG[key];
      const keyLevel = parseInt(keyConfig.level);
      const clearLevel = parseInt(config.level);

      if (keyLevel >= clearLevel) {
        newFilterState[keyConfig.stateKey] = null;
      }
    });

    // Update centralized filter state
    this.props.setFilterInteractions(newFilterState);

    const fallbackConfig = this.findHighestExistingBoundaryConfig(boundaryType);

    if (fallbackConfig) {
      // Update to parent boundary params using consolidated utility
      const paramInteractions = buildParamInteractionsFromBoundary(
        fallbackConfig.boundary,
        fallbackConfig.level,
        fallbackConfig.borderLevel
      );
      this.props.setParamInteractions(paramInteractions);

      if (fallbackConfig.boundary?.bbox) {
        await this.fitMapToBounds(fallbackConfig.boundary.bbox);
      }
    } else {
      // Reset all params to defaults (will restore initial CMS params if they exist)
      this.props.clearParamInteractions();

      // If there's an initial bbox from CMS, fit to it; otherwise clear bbox to use default viewport
      const { initialBbox } = this.props;
      if (initialBbox && initialBbox.length === 4) {
        await this.fitMapToBounds(initialBbox, true);
      } else {
        await this.resetToDefaultView();
      }
    }
  };

  shouldClearBoundary = (boundaryKey, changedBoundaryType) => {
    const changedLevel = this.getBoundaryLevel(changedBoundaryType);
    const currentLevel = this.getBoundaryLevel(boundaryKey);
    return currentLevel > changedLevel;
  };

  getBoundaryLevel = (boundaryType) => {
    const config = BOUNDARY_CONFIG[boundaryType];
    return config ? parseInt(config.level) : -1;
  };

  findHighestExistingBoundaryConfig = (clearedBoundaryType) => {
    const clearedLevel = this.getBoundaryLevel(clearedBoundaryType);

    for (let level = clearedLevel - 1; level >= 0; level--) {
      const boundaryType = this.getBoundaryTypeByLevel(level.toString());
      if (boundaryType && this.props.filterInteractions[BOUNDARY_CONFIG[boundaryType].stateKey]) {
        return {
          ...BOUNDARY_CONFIG[boundaryType],
          boundary: this.props.filterInteractions[BOUNDARY_CONFIG[boundaryType].stateKey]
        };
      }
    }

    return null;
  };

  getBoundaryTypeByLevel = (level) => {
    return Object.keys(BOUNDARY_CONFIG).find(
      key => BOUNDARY_CONFIG[key].level === level
    );
  };

  resetToDefaultView = async () => {
    const { setMapSettings } = this.props;
    const centerLng = 36.84;
    const centerLat = 5.73;
   const bboxPadding = 20; 

    const defaultBbox = [
      centerLng - bboxPadding, // left
      centerLat - bboxPadding, // bottom
      centerLng + bboxPadding, // right
      centerLat + bboxPadding  // top
    ];

    setMapSettings({
      canBound: true,
      bbox: defaultBbox
    });
  };

  fitMapToBounds = async (bbox, isFormatted = false) => {
    const { setMapSettings } = this.props;
    if (!bbox) return;

    const formattedBbox = isFormatted
      ? bbox
      : [bbox.left, bbox.bottom, bbox.right, bbox.top];

    // Validate bbox
    const [minX, minY, maxX, maxY] = formattedBbox;
    if (isNaN(minX) || isNaN(minY) || isNaN(maxX) || isNaN(maxY) || minX >= maxX || minY >= maxY) {
      console.error('Invalid bbox:', formattedBbox);
      return;
    }

    setMapSettings({
      canBound: true,
      bbox: [...formattedBbox]
    });
  };

  render() {
    const { selectedCountry, selectedSubBorder, selectedLowerBorder } = this.props.filterInteractions;
    const { boundaryData, setBoundaryData } = this.props;

    return (
      <div className="filter-panel-container">
        <div className="filter-grid">
          <div className="filter-column">
            <h3>Filter By Country</h3>
            <CountrySelector
              selectedCountry={selectedCountry}
              onChange={(country) => this.handleBoundaryChange('country', country)}
              onClear={() => this.clearBoundary('country')}
              boundaryData={boundaryData}
              setBoundaryData={setBoundaryData}
            />
          </div>

          {selectedCountry && (
            <div className="filter-column">
              <h3>Filter By Sub Border</h3>
              <SubBorderSelector
                country={selectedCountry}
                selectedSubBorder={selectedSubBorder}
                onChange={(subBorder) => this.handleBoundaryChange('subBorder', subBorder)}
                onClear={() => this.clearBoundary('subBorder')}
                boundaryData={boundaryData}
                setBoundaryData={setBoundaryData}
              />
            </div>
          )}

          {selectedSubBorder && (
            <div className="filter-column">
              <h3>Filter By Lower Border</h3>
              <LowerBorderSelector
                subBorder={selectedSubBorder}
                selectedLowerBorder={selectedLowerBorder}
                countryName={selectedCountry?.name}
                onChange={(lowerBorder) => this.handleBoundaryChange('lowerBorder', lowerBorder)}
                onClear={() => this.clearBoundary('lowerBorder')}
                boundaryData={boundaryData}
                setBoundaryData={setBoundaryData}
              />
            </div>
          )}
        </div>
      </div>
    );
  }
}

const mapStateToProps = (state) => ({
  stateBbox: state.map?.settings?.bbox || [],
  filterInteractions: state.map?.data?.filterInteractions || {
    selectedCountry: null,
    selectedSubBorder: null,
    selectedLowerBorder: null,
  },
  boundaryData: selectBoundaryData(state),
  initialBbox: selectInitialBbox(state),
  initialParamInteractions: selectInitialParamInteractions(state)
});

const mapDispatchToProps = {
  setDatasetParams,
  setMapSettings,
  setFilterInteractions,
  clearFilterInteractions,
  setParamInteractions,
  clearParamInteractions,
  setBoundaryData
};

export const FilterPanelContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(FilterPanelContainerComponent);


// =============================================================================
// FloodWatch Custom: WHCA Countries Filter
// WHCA = Uganda, Rwanda, South Sudan, Ethiopia, Sudan (5 countries)
// When selected, automatically zooms to and filters by all 5 countries as one region
// Also provides admin selectors filtered to only WHCA countries
// =============================================================================
const WHCA_COUNTRIES = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];

// WHCA-specific boundary selector that filters countries to WHCA only
const WHCACountrySelector = ({
  selectedCountry,
  whcaCountries,
  onChange,
  onClear,
}) => {
  const availableCountries = whcaCountries.filter(
    c => !selectedCountry || c.code !== selectedCountry.code
  );

  const dropdownOptions = [
    { label: '+ Select country', value: '' },
    ...availableCountries.map(country => ({
      label: country.name,
      value: country.code
    }))
  ];

  return (
    <div className="filter-container">
      {selectedCountry && (
        <FilterItem label={selectedCountry.name} onClear={onClear} />
      )}
      <Dropdown
        className="boundary-dropdown"
        theme="theme-dropdown-native"
        options={dropdownOptions}
        value=""
        onChange={(value) => {
          if (value) {
            const selected = whcaCountries.find(c => c.code === value);
            if (selected) onChange(selected);
          }
        }}
        native
      />
    </div>
  );
};

// WHCA Region selector using same pattern
const WHCARegionSelector = ({
  selectedRegion,
  regions,
  onChange,
  onClear,
  showOnlyIfParent,
  parentCode
}) => {
  if (showOnlyIfParent && !parentCode) return null;

  const availableRegions = regions.filter(
    r => !selectedRegion || r.code !== selectedRegion.code
  );

  const dropdownOptions = [
    { label: '+ Select region', value: '' },
    ...availableRegions.map(region => ({
      label: region.name,
      value: region.code
    }))
  ];

  return (
    <div className="filter-container">
      {selectedRegion && (
        <FilterItem label={selectedRegion.name} onClear={onClear} />
      )}
      <Dropdown
        className="boundary-dropdown"
        theme="theme-dropdown-native"
        options={dropdownOptions}
        value=""
        onChange={(value) => {
          if (value) {
            const selected = regions.find(r => r.code === value);
            if (selected) onChange(selected);
          }
        }}
        native
      />
    </div>
  );
};

// WHCA District selector using same pattern
const WHCADistrictSelector = ({
  selectedDistrict,
  districts,
  onChange,
  onClear,
  showOnlyIfParent,
  parentCode
}) => {
  if (showOnlyIfParent && !parentCode) return null;

  const availableDistricts = districts.filter(
    d => !selectedDistrict || d.code !== selectedDistrict.code
  );

  const dropdownOptions = [
    { label: '+ Select district', value: '' },
    ...availableDistricts.map(district => ({
      label: district.name,
      value: district.code
    }))
  ];

  return (
    <div className="filter-container">
      {selectedDistrict && (
        <FilterItem label={selectedDistrict.name} onClear={onClear} />
      )}
      <Dropdown
        className="boundary-dropdown"
        theme="theme-dropdown-native"
        options={dropdownOptions}
        value=""
        onChange={(value) => {
          if (value) {
            const selected = districts.find(d => d.code === value);
            if (selected) onChange(selected);
          }
        }}
        native
      />
    </div>
  );
};

class WHCAFilterContainerComponent extends React.Component {
  state = {
    loading: true,
    applied: false,
    whcaCountriesData: [],
    selectedCountry: null,
    selectedRegion: null,
    selectedDistrict: null,
    regions: [],
    districts: [],
  };

  componentDidMount() {
    this.applyWHCAFilter();
  }

  applyWHCAFilter = async () => {
    try {
      const data = await fetchAdminBoundaries(null, '', true, {
        boundaryData: this.props.boundaryData,
        setBoundaryData: this.props.setBoundaryData
      });

      // Filter to only WHCA countries and calculate combined bounds
      const whcaData = (Array.isArray(data) ? data : []).filter(item =>
        WHCA_COUNTRIES.includes(item.name)
      );

      if (whcaData.length > 0) {
        let minLeft = Infinity, minBottom = Infinity;
        let maxRight = -Infinity, maxTop = -Infinity;

        whcaData.forEach(item => {
          if (item.bbox) {
            minLeft = Math.min(minLeft, item.bbox.left);
            minBottom = Math.min(minBottom, item.bbox.bottom);
            maxRight = Math.max(maxRight, item.bbox.right);
            maxTop = Math.max(maxTop, item.bbox.top);
          }
        });

        // Zoom to WHCA region
        this.props.setMapSettings({
          canBound: true,
          bbox: [minLeft, minBottom, maxRight, maxTop]
        });

        // Set param interactions for WHCA filtering
        this.props.setParamInteractions({
          whca_filter: true,
          whca_countries: WHCA_COUNTRIES.join(',')
        });

        this.setState({ loading: false, applied: true, whcaCountriesData: whcaData });
      }
    } catch (error) {
      this.setState({ loading: false });
    }
  };

  handleCountryChange = async (country) => {
    if (!country) return;

    this.setState({ selectedCountry: country, selectedRegion: null, selectedDistrict: null, districts: [] });

    // Fetch regions for selected country using shared utility
    const regions = await fetchAdminBoundaries(0, country.name, true, {
      boundaryData: this.props.boundaryData,
      setBoundaryData: this.props.setBoundaryData
    });
    this.setState({ regions: Array.isArray(regions) ? regions : [] });

    // Update params using shared utility
    const paramInteractions = buildParamInteractionsFromBoundary(
      country, '0', '0', 'Admin',
      { country_name: country.name, region_name: '' }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(',')
    });

    // Zoom to country
    if (country.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [country.bbox.left, country.bbox.bottom, country.bbox.right, country.bbox.top]
      });
    }
  };

  handleRegionChange = async (region) => {
    if (!region) return;

    this.setState({ selectedRegion: region, selectedDistrict: null });

    // Fetch districts for selected region
    const districts = await fetchAdminBoundaries(1, region.name, true, {
      boundaryData: this.props.boundaryData,
      setBoundaryData: this.props.setBoundaryData,
      extraParams: {
        country_id: this.state.selectedCountry?.name || ''
      }
    });
    this.setState({ districts: Array.isArray(districts) ? districts : [] });

    // Update params using shared utility
    const paramInteractions = buildParamInteractionsFromBoundary(
      region, '1', '1', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: region.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(',')
    });

    // Zoom to region
    if (region.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [region.bbox.left, region.bbox.bottom, region.bbox.right, region.bbox.top]
      });
    }
  };

  handleDistrictChange = (district) => {
    if (!district) return;

    this.setState({ selectedDistrict: district });

    // Update params using shared utility
    const paramInteractions = buildParamInteractionsFromBoundary(
      district, '2', '2', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: this.state.selectedRegion.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(','),
      district_name: district.name
    });

    // Zoom to district
    if (district.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [district.bbox.left, district.bbox.bottom, district.bbox.right, district.bbox.top]
      });
    }
  };

  clearCountry = () => {
    this.setState({ selectedCountry: null, selectedRegion: null, selectedDistrict: null, regions: [], districts: [] });
    this.props.setParamInteractions({
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(','),
      country_name: '',
      region_name: '',
      district_name: '',
      admin_filter: false
    });
    this.applyWHCAFilter();
  };

  clearRegion = () => {
    this.setState({ selectedRegion: null, selectedDistrict: null, districts: [] });
    const paramInteractions = buildParamInteractionsFromBoundary(
      this.state.selectedCountry, '0', '0', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: '' }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(',')
    });
    if (this.state.selectedCountry?.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [this.state.selectedCountry.bbox.left, this.state.selectedCountry.bbox.bottom,
               this.state.selectedCountry.bbox.right, this.state.selectedCountry.bbox.top]
      });
    }
  };

  clearDistrict = () => {
    this.setState({ selectedDistrict: null });
    const paramInteractions = buildParamInteractionsFromBoundary(
      this.state.selectedRegion, '1', '1', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: this.state.selectedRegion.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      whca_filter: true,
      whca_countries: WHCA_COUNTRIES.join(',')
    });
    if (this.state.selectedRegion?.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [this.state.selectedRegion.bbox.left, this.state.selectedRegion.bbox.bottom,
               this.state.selectedRegion.bbox.right, this.state.selectedRegion.bbox.top]
      });
    }
  };

  render() {
    const { loading, applied, whcaCountriesData, selectedCountry, selectedRegion, selectedDistrict, regions, districts } = this.state;

    return (
      <div className="filter-panel-container">
        {loading && <p className="loading">Loading...</p>}

        {applied && (
          <div className="filter-grid">
            <div className="filter-column">
              <h3>Filter By Country</h3>
              <WHCACountrySelector
                selectedCountry={selectedCountry}
                whcaCountries={whcaCountriesData}
                onChange={this.handleCountryChange}
                onClear={this.clearCountry}
              />
            </div>

            {selectedCountry && (
              <div className="filter-column">
                <h3>Filter By Region</h3>
                <WHCARegionSelector
                  selectedRegion={selectedRegion}
                  regions={regions}
                  onChange={this.handleRegionChange}
                  onClear={this.clearRegion}
                  showOnlyIfParent={true}
                  parentCode={selectedCountry?.code}
                />
              </div>
            )}

            {selectedRegion && (
              <div className="filter-column">
                <h3>Filter By District</h3>
                <WHCADistrictSelector
                  selectedDistrict={selectedDistrict}
                  districts={districts}
                  onChange={this.handleDistrictChange}
                  onClear={this.clearDistrict}
                  showOnlyIfParent={true}
                  parentCode={selectedRegion?.code}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
}

export const WHCAFilterContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(WHCAFilterContainerComponent);


// =============================================================================
// FloodWatch Custom: Grid Cells Filter
// Uses 0.25 degree grid cells (gha.grid_025dd) for clustering and analysis
// Grid cells have pre-computed admin boundaries for fast filtering
// =============================================================================

class GridFilterContainerComponent extends React.Component {
  state = {
    loading: false,
    selectedCountry: null,
    selectedRegion: null,
    selectedGridCell: null,
    gridCells: [],
    regions: [],
  };

  handleCountryChange = async (country) => {
    if (!country) return;

    this.setState({
      selectedCountry: country,
      selectedRegion: null,
      selectedGridCell: null,
      gridCells: [],
      loading: true
    });

    // Fetch regions for selected country
    const regions = await fetchAdminBoundaries(0, country.name, true, {
      boundaryData: this.props.boundaryData,
      setBoundaryData: this.props.setBoundaryData
    });

    this.setState({ regions: Array.isArray(regions) ? regions : [], loading: false });

    // Set param interactions for country-level grid filtering
    this.props.setParamInteractions({
      grid_filter: true,
      country_name: country.name,
      region_name: '',
      admin_level: '0'
    });

    // Zoom to country
    if (country.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [country.bbox.left, country.bbox.bottom, country.bbox.right, country.bbox.top]
      });
    }
  };

  handleRegionChange = async (region) => {
    if (!region) return;

    this.setState({
      selectedRegion: region,
      selectedGridCell: null,
      loading: true
    });

    // Fetch grid cells for this region from the API
    try {
      const response = await fetch(
        `/api/grid-cells/?country=${encodeURIComponent(this.state.selectedCountry.name)}&region=${encodeURIComponent(region.name)}`
      );
      if (response.ok) {
        const gridCells = await response.json();
        this.setState({ gridCells: Array.isArray(gridCells) ? gridCells : [] });
      }
    } catch (error) {
      console.error('Error fetching grid cells:', error);
      this.setState({ gridCells: [] });
    }

    this.setState({ loading: false });

    // Set param interactions for region-level grid filtering
    this.props.setParamInteractions({
      grid_filter: true,
      country_name: this.state.selectedCountry.name,
      region_name: region.name,
      admin_level: '1'
    });

    // Zoom to region
    if (region.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [region.bbox.left, region.bbox.bottom, region.bbox.right, region.bbox.top]
      });
    }
  };

  handleGridCellSelect = (gridCell) => {
    if (!gridCell) return;

    this.setState({ selectedGridCell: gridCell });

    // Set param interactions for grid cell filtering
    this.props.setParamInteractions({
      grid_filter: true,
      grid_id: gridCell.id,
      country_name: this.state.selectedCountry?.name || '',
      region_name: this.state.selectedRegion?.name || '',
      admin_level: 'grid'
    });

    // Zoom to grid cell
    if (gridCell.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: gridCell.bbox
      });
    }
  };

  clearCountry = () => {
    this.setState({
      selectedCountry: null,
      selectedRegion: null,
      selectedGridCell: null,
      regions: [],
      gridCells: []
    });
    this.props.clearParamInteractions();
  };

  clearRegion = () => {
    this.setState({
      selectedRegion: null,
      selectedGridCell: null,
      gridCells: []
    });

    this.props.setParamInteractions({
      grid_filter: true,
      country_name: this.state.selectedCountry?.name || '',
      region_name: '',
      admin_level: '0'
    });

    if (this.state.selectedCountry?.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [
          this.state.selectedCountry.bbox.left,
          this.state.selectedCountry.bbox.bottom,
          this.state.selectedCountry.bbox.right,
          this.state.selectedCountry.bbox.top
        ]
      });
    }
  };

  clearGridCell = () => {
    this.setState({ selectedGridCell: null });

    this.props.setParamInteractions({
      grid_filter: true,
      country_name: this.state.selectedCountry?.name || '',
      region_name: this.state.selectedRegion?.name || '',
      admin_level: '1'
    });

    if (this.state.selectedRegion?.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [
          this.state.selectedRegion.bbox.left,
          this.state.selectedRegion.bbox.bottom,
          this.state.selectedRegion.bbox.right,
          this.state.selectedRegion.bbox.top
        ]
      });
    }
  };

  render() {
    const { loading, selectedCountry, selectedRegion, selectedGridCell, regions, gridCells } = this.state;
    const { boundaryData, setBoundaryData } = this.props;

    return (
      <div className="filter-panel-container">
        <div className="grid-filter-info">
          <p className="info-text">Select a region to view 0.25° grid cells</p>
        </div>

        <div className="filter-grid">
          <div className="filter-column">
            <h3>Select Country</h3>
            <CountrySelector
              selectedCountry={selectedCountry}
              onChange={this.handleCountryChange}
              onClear={this.clearCountry}
              boundaryData={boundaryData}
              setBoundaryData={setBoundaryData}
            />
          </div>

          {selectedCountry && (
            <div className="filter-column">
              <h3>Select Region</h3>
              <BoundarySelector
                adminLevel={0}
                parentCode={selectedCountry.code}
                selectedBoundary={selectedRegion}
                placeholder="+ Select region"
                onChange={this.handleRegionChange}
                onClear={this.clearRegion}
                boundaryData={boundaryData}
                setBoundaryData={setBoundaryData}
                showOnlyIfParent={true}
              />
            </div>
          )}

          {selectedRegion && (
            <div className="filter-column">
              <h3>Select Grid Cell</h3>
              {loading ? (
                <p className="loading">Loading grid cells...</p>
              ) : gridCells.length > 0 ? (
                <div className="filter-container">
                  {selectedGridCell && (
                    <FilterItem
                      label={`Grid ${selectedGridCell.id}`}
                      onClear={this.clearGridCell}
                    />
                  )}
                  <Dropdown
                    className="boundary-dropdown"
                    theme="theme-dropdown-native"
                    options={[
                      { label: '+ Select grid cell', value: '' },
                      ...gridCells
                        .filter(g => !selectedGridCell || g.id !== selectedGridCell.id)
                        .map(g => ({
                          label: `Grid ${g.id} (${g.xcol}, ${g.yrow})`,
                          value: g.id
                        }))
                    ]}
                    value=""
                    onChange={(value) => {
                      if (value) {
                        const selected = gridCells.find(g => g.id === parseInt(value));
                        if (selected) this.handleGridCellSelect(selected);
                      }
                    }}
                    native
                  />
                </div>
              ) : (
                <p className="no-data">No grid cells in this region</p>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }
}

export const GridFilterContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(GridFilterContainerComponent);
