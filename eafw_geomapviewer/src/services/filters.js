import React, { useState, useEffect } from 'react';
import { connect } from 'react-redux';
import {
  setMapSettings,
  setParamInteractions,
  clearParamInteractions,
  setBoundaryData,
} from '@/components/map/actions';
import { buildParamInteractionsFromBoundary } from '@/utils/params';
import { fetchGenericBoundaries } from '@/utils/boundary-utils';
import { selectBoundaryData } from '@/components/map/selectors';
import Dropdown from '@/components/ui/dropdown';
import '@/styles/filters.css';

const FilterItem = ({ label, onClear }) => (
  <div className="filter-item">
    <span>{label}</span>
    <button onClick={onClear} className="filter-clear">×</button>
  </div>
);

const PROJECT_OPTIONS = [
  { label: 'All Region', value: 'all' },
  { label: 'WHCA', value: 'whca' },
];

const WHCA_BBOX = [21.838949204000073, -2.839972733999957, 47.958229065000126, 23.14514700000001];
const WHCA_PROJECT_COUNTRIES = 'SD,SS,UG,ET,RW';

const ProjectFilterPanelContainerComponent = ({
  configBounds,
  setMapSettings,
  setParamInteractions,
  clearParamInteractions,
}) => {
  // Auto-select scope from URL query param (e.g., ?scope=whca)
  const urlScope = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search).get('scope') || 'all'
    : 'all';
  const [selectedProject, setSelectedProject] = useState(urlScope);
  const initializedRef = React.useRef(false);

  const applyProjectScope = (value) => {
    setSelectedProject(value);
    clearParamInteractions();

    if (value === 'whca') {
      setParamInteractions({
        scope: 'whca',
        project_countries: WHCA_PROJECT_COUNTRIES,
      });
      setMapSettings({ canBound: true, bbox: WHCA_BBOX });
      return;
    }

    if (configBounds?.length) {
      setMapSettings({ canBound: true, bbox: configBounds });
    }
  };

  // Apply URL scope on first render
  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      if (urlScope !== 'all') {
        // Small delay to ensure redux is ready
        setTimeout(() => applyProjectScope(urlScope), 500);
      } else {
        clearParamInteractions();
        if (configBounds?.length) {
          setMapSettings({ canBound: true, bbox: configBounds });
        }
      }
    }
  }, [configBounds]);

  return (
    <div className="filter-panel-container">
      <div className="filter-grid">
        <div className="filter-column">
          <h3>Project</h3>
          <div className="filter-container">
            <Dropdown
              className="boundary-dropdown"
              theme="theme-dropdown-native"
              options={PROJECT_OPTIONS}
              value={selectedProject}
              onChange={applyProjectScope}
              native
            />
          </div>
        </div>
      </div>
    </div>
  );
};

const GenericBoundarySelector = ({
  apiUrl,
  levelConfig,
  parentCode,
  ancestorMap,
  selectedBoundary,
  onChange,
  onClear,
  boundaryData,
  setBoundaryData,
}) => {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    fetchGenericBoundaries(apiUrl, levelConfig, parentCode, { boundaryData, setBoundaryData, ancestorMap })
      .then((data) => setOptions(Array.isArray(data) ? data : []));
  }, [apiUrl, levelConfig.admin_level, parentCode]); // eslint-disable-line react-hooks/exhaustive-deps

  const dropdownOptions = [
    { label: levelConfig.placeholder, value: '' },
    ...options
      .filter((b) => !selectedBoundary || b.code !== selectedBoundary.code)
      .map((b) => ({ label: b.name, value: b.code })),
  ];

  return (
    <div className="filter-container">
      {selectedBoundary && (
        <FilterItem label={selectedBoundary.name} onClear={onClear} />
      )}
      <Dropdown
        className="boundary-dropdown"
        theme="theme-dropdown-native"
        options={dropdownOptions}
        value=""
        onChange={(value) => {
          const sel = options.find((b) => b.code === value);
          if (sel) onChange(sel);
        }}
        native
      />
    </div>
  );
};

// Build the initial selectedBoundaries array from consecutive fixed_code levels.
// Stops at the first level without a fixed_code so visible dropdowns cascade correctly.
function buildInitialSelected(filterTypeConfig) {
  const initial = [];
  for (const levelConfig of filterTypeConfig.levels) {
    if (levelConfig.fixed_code) {
      initial.push({ code: levelConfig.fixed_code, name: levelConfig.fixed_code });
    } else {
      break;
    }
  }
  return initial;
}

class GenericFilterPanelContainerComponent extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      selectedBoundaries: buildInitialSelected(props.filterTypeConfig),
    };
  }

  componentDidMount() {
    const { filterTypeConfig, boundaryData, setBoundaryData } = this.props;
    const { selectedBoundaries } = this.state;
    this.props.clearParamInteractions();
    if (selectedBoundaries.length === 0) return;

    const deepestIndex = selectedBoundaries.length - 1;
    const deepestLevel = filterTypeConfig.levels[deepestIndex];
    const deepestBoundary = selectedBoundaries[deepestIndex];
    const rootCode = selectedBoundaries[0]?.code || '';
    const projectName = filterTypeConfig.fixed_project_name || rootCode;

    this.props.setParamInteractions(
      buildParamInteractionsFromBoundary(
        deepestBoundary,
        deepestLevel.admin_level,
        deepestLevel.border_level,
        projectName
      )
    );

    // Fetch boundary data to fit map to the fixed boundary's bbox on load.
    // Force include_bbox so we always get coordinates regardless of level config.
    const resolvedLevelConfig = {
      ...deepestLevel,
      code_field: deepestLevel.code_field || filterTypeConfig.default_code_field || 'code',
      name_field: deepestLevel.name_field || filterTypeConfig.default_name_field || 'name',
      include_bbox: true,
    };
    const parentCode = deepestIndex === 0 ? '' : selectedBoundaries[deepestIndex - 1]?.code;
    const ancestorMap = {};
    selectedBoundaries.slice(0, deepestIndex).forEach((boundary, i) => {
      const varName = filterTypeConfig.levels[i]?.variable_name;
      if (varName) ancestorMap[varName] = boundary?.code || '';
    });

    fetchGenericBoundaries(
      filterTypeConfig.boundary_api_url,
      resolvedLevelConfig,
      parentCode,
      { boundaryData, setBoundaryData, ancestorMap }
    ).then((data) => {
      const match = data.find((b) => b.code === deepestBoundary.code);
      if (match?.bbox) {
        const { left, bottom, right, top } = match.bbox;
        this.props.setMapSettings({ canBound: true, bbox: [left, bottom, right, top] });
        // Store bbox on the fixed boundary entry so handleClear can fit to it later
        this.setState((prevState) => {
          const updated = [...prevState.selectedBoundaries];
          updated[deepestIndex] = { ...updated[deepestIndex], bbox: match.bbox };
          return { selectedBoundaries: updated };
        });
      }
    });
  }

  handleSelect = (levelIndex, boundary) => {
    const { filterTypeConfig } = this.props;
    const levelConfig = filterTypeConfig.levels[levelIndex];

    const newSelected = [
      ...this.state.selectedBoundaries.slice(0, levelIndex),
      boundary,
    ];
    this.setState({ selectedBoundaries: newSelected });

    const rootCode = newSelected[0]?.code || '';
    const projectName = filterTypeConfig.fixed_project_name || rootCode;

    this.props.setParamInteractions(
      buildParamInteractionsFromBoundary(
        boundary,
        levelConfig.admin_level,
        levelConfig.border_level,
        projectName
      )
    );

    if (boundary.bbox) {
      const { left, bottom, right, top } = boundary.bbox;
      this.props.setMapSettings({ canBound: true, bbox: [left, bottom, right, top] });
    }
  };

  handleClear = (levelIndex) => {
    const { filterTypeConfig } = this.props;
    const newSelected = this.state.selectedBoundaries.slice(0, levelIndex);
    this.setState({ selectedBoundaries: newSelected });

    if (levelIndex === 0) {
      this.props.clearParamInteractions();
      // Fit back to the default regional bounds
      const { configBounds } = this.props;
      if (configBounds && configBounds.length) {
        this.props.setMapSettings({ canBound: true, bbox: configBounds });
      }
    } else {
      const parent = newSelected[levelIndex - 1];
      const parentLevel = filterTypeConfig.levels[levelIndex - 1];
      const rootCode = newSelected[0]?.code || '';
      const projectName = filterTypeConfig.fixed_project_name || rootCode;
      this.props.setParamInteractions(
        buildParamInteractionsFromBoundary(
          parent,
          parentLevel.admin_level,
          parentLevel.border_level,
          projectName
        )
      );
      if (parent.bbox) {
        const { left, bottom, right, top } = parent.bbox;
        this.props.setMapSettings({ canBound: true, bbox: [left, bottom, right, top] });
      }
    }
  };

  render() {
    const { filterTypeConfig, boundaryData, setBoundaryData } = this.props;
    const { selectedBoundaries } = this.state;

    return (
      <div className="filter-panel-container">
        <div className="filter-grid">
          {filterTypeConfig.levels.map((levelConfig, index) => {
            if (index > 0 && !selectedBoundaries[index - 1]) return null;
            // Fixed levels are pre-selected on mount — hide their dropdown entirely.
            if (levelConfig.fixed_code) return null;

            const parentCode = index === 0 ? '' : selectedBoundaries[index - 1]?.code;

            // Build a name→code map from all ancestor selections so child levels can
            // reference them by variable_name in extra_api_params (e.g. {cluster}).
            const ancestorMap = {};
            selectedBoundaries.slice(0, index).forEach((boundary, i) => {
              const varName = filterTypeConfig.levels[i]?.variable_name;
              if (varName) ancestorMap[varName] = boundary?.code || '';
            });

            // Merge filter-type defaults into level config so individual levels
            // only need to specify code_field/name_field when overriding.
            const resolvedLevelConfig = {
              ...levelConfig,
              code_field: levelConfig.code_field || filterTypeConfig.default_code_field || 'code',
              name_field: levelConfig.name_field || filterTypeConfig.default_name_field || 'name',
            };

            return (
              <div key={index} className="filter-column">
                <h3>{levelConfig.heading}</h3>
                <GenericBoundarySelector
                  apiUrl={filterTypeConfig.boundary_api_url}
                  levelConfig={resolvedLevelConfig}
                  parentCode={parentCode}
                  ancestorMap={ancestorMap}
                  selectedBoundary={selectedBoundaries[index] || null}
                  onChange={(b) => this.handleSelect(index, b)}
                  onClear={() => this.handleClear(index)}
                  boundaryData={boundaryData}
                  setBoundaryData={setBoundaryData}
                />
              </div>
            );
          })}
        </div>
      </div>
    );
  }
}

const mapStateToProps = (state) => ({
  boundaryData: selectBoundaryData(state),
  configBounds: state.config?.bounds || [],
});

const mapDispatchToProps = {
  setMapSettings,
  setParamInteractions,
  clearParamInteractions,
  setBoundaryData,
};

export const GenericFilterPanelContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(GenericFilterPanelContainerComponent);

export const ProjectFilterPanelContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(ProjectFilterPanelContainerComponent);
