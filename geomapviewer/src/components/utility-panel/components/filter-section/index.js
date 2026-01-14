import { connect } from 'react-redux';
import Component from './component';
import { setSelectedFilterType } from '@/components/utility-panel/actions';

export default connect(null, { setSelectedFilterType })(Component);
