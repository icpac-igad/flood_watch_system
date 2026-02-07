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

// Convenience wrappers
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

// =============================================================================
// FloodWatch: Project-based Filter
// Projects define a set of countries with their full admin hierarchy.
// Selecting a project scopes the map to those countries, then allows
// drilling down through Country → Region → District.
// =============================================================================
const PROJECTS = {
  WHCA: {
    label: 'WHCA',
    countries: ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'],
  },
};

class ProjectFilterContainerComponent extends React.Component {
  state = {
    loading: false,
    selectedProject: null,
    projectCountriesData: [],
    selectedCountry: null,
    selectedRegion: null,
    selectedDistrict: null,
    regions: [],
    districts: [],
  };

  applyProject = async (projectKey) => {
    const project = PROJECTS[projectKey];
    if (!project) return;

    this.setState({ loading: true, selectedProject: projectKey,
      selectedCountry: null, selectedRegion: null, selectedDistrict: null,
      regions: [], districts: [], projectCountriesData: [] });

    try {
      const data = await fetchAdminBoundaries(null, '', true, {
        boundaryData: this.props.boundaryData,
        setBoundaryData: this.props.setBoundaryData
      });

      const projectData = (Array.isArray(data) ? data : []).filter(item =>
        project.countries.includes(item.name)
      );

      if (projectData.length > 0) {
        let minLeft = Infinity, minBottom = Infinity;
        let maxRight = -Infinity, maxTop = -Infinity;

        projectData.forEach(item => {
          if (item.bbox) {
            minLeft = Math.min(minLeft, item.bbox.left);
            minBottom = Math.min(minBottom, item.bbox.bottom);
            maxRight = Math.max(maxRight, item.bbox.right);
            maxTop = Math.max(maxTop, item.bbox.top);
          }
        });

        this.props.setMapSettings({
          canBound: true,
          bbox: [minLeft, minBottom, maxRight, maxTop]
        });

        this.props.setParamInteractions({
          project_filter: true,
          project_countries: project.countries.join(',')
        });
      }

      this.setState({ loading: false, projectCountriesData: projectData });
    } catch (error) {
      this.setState({ loading: false });
    }
  };

  clearProject = () => {
    this.setState({
      selectedProject: null, projectCountriesData: [],
      selectedCountry: null, selectedRegion: null, selectedDistrict: null,
      regions: [], districts: []
    });
    this.props.clearParamInteractions();

    const { initialBbox } = this.props;
    if (initialBbox && initialBbox.length === 4) {
      this.props.setMapSettings({ canBound: true, bbox: [...initialBbox] });
    }
  };

  handleCountryChange = async (country) => {
    if (!country) return;

    const project = PROJECTS[this.state.selectedProject];
    this.setState({ selectedCountry: country, selectedRegion: null, selectedDistrict: null, districts: [] });

    const regions = await fetchAdminBoundaries(0, country.name, true, {
      boundaryData: this.props.boundaryData,
      setBoundaryData: this.props.setBoundaryData
    });
    this.setState({ regions: Array.isArray(regions) ? regions : [] });

    const paramInteractions = buildParamInteractionsFromBoundary(
      country, '0', '0', 'Admin',
      { country_name: country.name, region_name: '' }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      project_filter: true,
      project_countries: project.countries.join(',')
    });

    if (country.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [country.bbox.left, country.bbox.bottom, country.bbox.right, country.bbox.top]
      });
    }
  };

  handleRegionChange = async (region) => {
    if (!region) return;

    const project = PROJECTS[this.state.selectedProject];
    this.setState({ selectedRegion: region, selectedDistrict: null });

    const districts = await fetchAdminBoundaries(1, region.name, true, {
      boundaryData: this.props.boundaryData,
      setBoundaryData: this.props.setBoundaryData,
      extraParams: { country_id: this.state.selectedCountry?.name || '' }
    });
    this.setState({ districts: Array.isArray(districts) ? districts : [] });

    const paramInteractions = buildParamInteractionsFromBoundary(
      region, '1', '1', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: region.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      project_filter: true,
      project_countries: project.countries.join(',')
    });

    if (region.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [region.bbox.left, region.bbox.bottom, region.bbox.right, region.bbox.top]
      });
    }
  };

  handleDistrictChange = (district) => {
    if (!district) return;

    const project = PROJECTS[this.state.selectedProject];
    this.setState({ selectedDistrict: district });

    const paramInteractions = buildParamInteractionsFromBoundary(
      district, '2', '2', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: this.state.selectedRegion.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      project_filter: true,
      project_countries: project.countries.join(','),
      district_name: district.name
    });

    if (district.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [district.bbox.left, district.bbox.bottom, district.bbox.right, district.bbox.top]
      });
    }
  };

  clearCountry = () => {
    this.setState({ selectedCountry: null, selectedRegion: null, selectedDistrict: null, regions: [], districts: [] });
    const project = PROJECTS[this.state.selectedProject];
    this.props.setParamInteractions({
      project_filter: true,
      project_countries: project.countries.join(','),
      country_name: '',
      region_name: '',
      district_name: '',
      admin_filter: false
    });
    this.applyProject(this.state.selectedProject);
  };

  clearRegion = () => {
    this.setState({ selectedRegion: null, selectedDistrict: null, districts: [] });
    const project = PROJECTS[this.state.selectedProject];
    const paramInteractions = buildParamInteractionsFromBoundary(
      this.state.selectedCountry, '0', '0', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: '' }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      project_filter: true,
      project_countries: project.countries.join(',')
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
    const project = PROJECTS[this.state.selectedProject];
    const paramInteractions = buildParamInteractionsFromBoundary(
      this.state.selectedRegion, '1', '1', 'Admin',
      { country_name: this.state.selectedCountry.name, region_name: this.state.selectedRegion.name }
    );
    this.props.setParamInteractions({
      ...paramInteractions,
      project_filter: true,
      project_countries: project.countries.join(',')
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
    const { loading, selectedProject, projectCountriesData,
      selectedCountry, selectedRegion, selectedDistrict, regions, districts } = this.state;

    const projectOptions = [
      { label: '+ Select project', value: '' },
      ...Object.keys(PROJECTS).map(key => ({
        label: PROJECTS[key].label,
        value: key
      }))
    ];

    const availableCountries = projectCountriesData.filter(
      c => !selectedCountry || c.code !== selectedCountry.code
    );
    const availableRegions = regions.filter(
      r => !selectedRegion || r.code !== selectedRegion.code
    );
    const availableDistricts = districts.filter(
      d => !selectedDistrict || d.code !== selectedDistrict.code
    );

    return (
      <div className="filter-panel-container">
        <div className="filter-grid">
          <div className="filter-column">
            <h3>Project Name</h3>
            <div className="filter-container">
              {selectedProject && (
                <FilterItem label={PROJECTS[selectedProject].label} onClear={this.clearProject} />
              )}
              <Dropdown
                className="boundary-dropdown"
                theme="theme-dropdown-native"
                options={projectOptions}
                value=""
                onChange={(value) => { if (value) this.applyProject(value); }}
                native
              />
            </div>
          </div>

          {selectedProject && !loading && projectCountriesData.length > 0 && (
            <div className="filter-column">
              <h3>Country</h3>
              <div className="filter-container">
                {selectedCountry && (
                  <FilterItem label={selectedCountry.name} onClear={this.clearCountry} />
                )}
                <Dropdown
                  className="boundary-dropdown"
                  theme="theme-dropdown-native"
                  options={[
                    { label: '+ Select country', value: '' },
                    ...availableCountries.map(c => ({ label: c.name, value: c.code }))
                  ]}
                  value=""
                  onChange={(value) => {
                    if (value) {
                      const selected = projectCountriesData.find(c => c.code === value);
                      if (selected) this.handleCountryChange(selected);
                    }
                  }}
                  native
                />
              </div>
            </div>
          )}

          {selectedCountry && regions.length > 0 && (
            <div className="filter-column">
              <h3>Region</h3>
              <div className="filter-container">
                {selectedRegion && (
                  <FilterItem label={selectedRegion.name} onClear={this.clearRegion} />
                )}
                <Dropdown
                  className="boundary-dropdown"
                  theme="theme-dropdown-native"
                  options={[
                    { label: '+ Select region', value: '' },
                    ...availableRegions.map(r => ({ label: r.name, value: r.code }))
                  ]}
                  value=""
                  onChange={(value) => {
                    if (value) {
                      const selected = regions.find(r => r.code === value);
                      if (selected) this.handleRegionChange(selected);
                    }
                  }}
                  native
                />
              </div>
            </div>
          )}

          {selectedRegion && districts.length > 0 && (
            <div className="filter-column">
              <h3>District</h3>
              <div className="filter-container">
                {selectedDistrict && (
                  <FilterItem label={selectedDistrict.name} onClear={this.clearDistrict} />
                )}
                <Dropdown
                  className="boundary-dropdown"
                  theme="theme-dropdown-native"
                  options={[
                    { label: '+ Select district', value: '' },
                    ...availableDistricts.map(d => ({ label: d.name, value: d.code }))
                  ]}
                  value=""
                  onChange={(value) => {
                    if (value) {
                      const selected = districts.find(d => d.code === value);
                      if (selected) this.handleDistrictChange(selected);
                    }
                  }}
                  native
                />
              </div>
            </div>
          )}
        </div>

        {loading && <p className="loading">Loading project data...</p>}
      </div>
    );
  }
}

export const ProjectFilterContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(ProjectFilterContainerComponent);


// =============================================================================
// FloodWatch Custom: Watershed/Basin Filter
// Uses HydroSHEDS Level 6 basins for spatial filtering by watershed
// =============================================================================

class WatershedFilterContainerComponent extends React.Component {
  state = {
    loading: true,
    basins: [],
    selectedBasin: null,
  };

  componentDidMount() {
    this.loadBasins();
  }

  loadBasins = async () => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
      const response = await fetch(`${apiBase}/api/v1/basins/list?with_points=true`);
      if (response.ok) {
        const data = await response.json();
        this.setState({ basins: data.basins || [], loading: false });
      } else {
        this.setState({ loading: false });
      }
    } catch (error) {
      console.error('Error fetching basins:', error);
      this.setState({ loading: false });
    }
  };

  handleBasinChange = (basin) => {
    if (!basin) return;

    this.setState({ selectedBasin: basin });

    // Set param interactions for basin filtering
    this.props.setParamInteractions({
      basin_filter: true,
      basin_id: basin.hybas_id,
      admin_filter: false,
      whca_filter: false,
      country_name: '',
      region_name: '',
      district_name: '',
    });

    // Zoom to basin bbox
    if (basin.bbox) {
      this.props.setMapSettings({
        canBound: true,
        bbox: [basin.bbox.west, basin.bbox.south, basin.bbox.east, basin.bbox.north],
      });
    }
  };

  clearBasin = () => {
    this.setState({ selectedBasin: null });
    this.props.clearParamInteractions();

    // Reset to default view
    const { initialBbox } = this.props;
    if (initialBbox && initialBbox.length === 4) {
      this.props.setMapSettings({ canBound: true, bbox: [...initialBbox] });
    }
  };

  render() {
    const { loading, basins, selectedBasin } = this.state;

    return (
      <div className="filter-panel-container">
        {loading && <p className="loading">Loading basins...</p>}

        {!loading && (
          <div className="filter-grid">
            <div className="filter-column">
              <h3>Filter By Watershed Basin</h3>
              <div className="filter-container">
                {selectedBasin && (
                  <FilterItem
                    label={`Basin ${selectedBasin.hybas_id} (${selectedBasin.point_count} pts)`}
                    onClear={this.clearBasin}
                  />
                )}
                <Dropdown
                  className="boundary-dropdown"
                  theme="theme-dropdown-native"
                  options={[
                    { label: '+ Select basin', value: '' },
                    ...basins
                      .filter(b => !selectedBasin || b.hybas_id !== selectedBasin.hybas_id)
                      .map(b => ({
                        label: `Basin ${b.hybas_id} (${b.point_count} pts, ${Math.round(b.up_area)} km²)`,
                        value: String(b.hybas_id),
                      })),
                  ]}
                  value=""
                  onChange={(value) => {
                    if (value) {
                      const selected = basins.find(b => String(b.hybas_id) === value);
                      if (selected) this.handleBasinChange(selected);
                    }
                  }}
                  native
                />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
}

export const WatershedFilterContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(WatershedFilterContainerComponent);


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
