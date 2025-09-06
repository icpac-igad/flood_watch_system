from django.test import TestCase
from django.contrib.gis.geos import MultiPolygon, Polygon, Point
from rest_framework.test import APITestCase
from rest_framework import status
from Impact.models import (
    AffectedPopulation, ImpactedGDP, AffectedCrops, 
    AffectedRoads, DisplacedPopulation, AffectedLivestock,
    AffectedGrazingLand, SectorData, SectorForecast,
    WaterBodies, RiverSection, Admin1
)
from datetime import datetime
import json


class BaseImpactModelTest(TestCase):
    """Test the abstract base model functionality through concrete models."""
    
    def setUp(self):
        # Create a test polygon
        self.test_polygon = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        )
        
        # Common test data for all impact models
        self.impact_data = {
            'gid_0': 'KEN',
            'name_0': 'Kenya',
            'name_1': 'Nairobi',
            'engtype_1': 'County',
            'lack_cc': 0.45,
            'cod': 'KE',
            'stock': 1000000.0,
            'flood_tot': 50000.0,
            'flood_perc': 5.0,
            'geom': self.test_polygon
        }
    
    def test_affected_population_creation(self):
        """Test creating an AffectedPopulation instance."""
        pop = AffectedPopulation.objects.create(**self.impact_data)
        self.assertEqual(str(pop), "Nairobi - AffectedPopulation")
        self.assertEqual(pop.name_1, "Nairobi")
        self.assertEqual(pop.flood_perc, 5.0)
    
    def test_impacted_gdp_creation(self):
        """Test creating an ImpactedGDP instance."""
        gdp = ImpactedGDP.objects.create(**self.impact_data)
        self.assertEqual(str(gdp), "Nairobi - ImpactedGDP")
        self.assertEqual(gdp.stock, 1000000.0)
    
    def test_affected_crops_creation(self):
        """Test creating an AffectedCrops instance."""
        crops = AffectedCrops.objects.create(**self.impact_data)
        self.assertEqual(str(crops), "Nairobi - AffectedCrops")
        self.assertEqual(crops.flood_tot, 50000.0)
    
    def test_model_inheritance(self):
        """Test that all impact models inherit from BaseImpactModel."""
        models_to_test = [
            AffectedPopulation, ImpactedGDP, AffectedCrops,
            AffectedRoads, DisplacedPopulation, AffectedLivestock,
            AffectedGrazingLand
        ]
        
        for model_class in models_to_test:
            instance = model_class.objects.create(**self.impact_data)
            # Test common fields exist
            self.assertTrue(hasattr(instance, 'gid_0'))
            self.assertTrue(hasattr(instance, 'name_0'))
            self.assertTrue(hasattr(instance, 'geom'))
            self.assertTrue(hasattr(instance, 'flood_perc'))


class SectorDataModelTest(TestCase):
    """Test SectorData model."""
    
    def setUp(self):
        self.sector_data = {
            'sec_code': 10001,
            'sec_name': 'Nairobi River Section',
            'basin': 'Athi',
            'domain': 'Kenya',
            'admin_b_l1': 'Nairobi',
            'admin_b_l2': 'Westlands',
            'sec_rs': 'NRB_001',
            'area': 126.5,
            'lat': -1.2921,
            'lon': 36.8219,
            'q_thr1': 50.0,
            'q_thr2': 100.0,
            'q_thr3': 150.0,
            'geom': Point(36.8219, -1.2921)
        }
    
    def test_sector_data_creation(self):
        """Test creating a SectorData instance."""
        sector = SectorData.objects.create(**self.sector_data)
        self.assertEqual(str(sector), "Nairobi River Section (10001)")
        self.assertEqual(sector.basin, "Athi")
        self.assertEqual(sector.q_thr1, 50.0)


class SectorForecastModelTest(TestCase):
    """Test SectorForecast model."""
    
    def setUp(self):
        # Create a sector first
        self.sector = SectorData.objects.create(
            sec_code=10001,
            sec_name='Test Section',
            basin='Test Basin',
            domain='Test Domain',
            admin_b_l1='Test Admin',
            sec_rs='TEST_001',
            area=100.0,
            lat=-1.0,
            lon=36.0,
            q_thr1=50.0,
            q_thr2=100.0,
            q_thr3=150.0,
            geom=Point(36.0, -1.0)
        )
    
    def test_sector_forecast_creation(self):
        """Test creating a SectorForecast instance."""
        forecast = SectorForecast.objects.create(
            sector=self.sector,
            model_type='GFS',
            time_point=datetime(2024, 1, 20, 12, 0),
            forecast_value=75.5
        )
        self.assertEqual(
            str(forecast), 
            "Test Section - GFS - 2024-01-20 12:00:00"
        )
        self.assertEqual(forecast.model_type, 'GFS')
        self.assertEqual(forecast.forecast_value, 75.5)
    
    def test_unique_constraint(self):
        """Test unique constraint on sector, model_type, and time_point."""
        SectorForecast.objects.create(
            sector=self.sector,
            model_type='GFS',
            time_point=datetime(2024, 1, 20, 12, 0),
            forecast_value=75.5
        )
        
        # Attempt to create duplicate should fail
        with self.assertRaises(Exception):
            SectorForecast.objects.create(
                sector=self.sector,
                model_type='GFS',
                time_point=datetime(2024, 1, 20, 12, 0),
                forecast_value=80.0
            )


class WaterBodiesModelTest(TestCase):
    """Test WaterBodies model."""
    
    def test_water_body_creation(self):
        """Test creating a WaterBodies instance."""
        water_body = WaterBodies.objects.create(
            fid=1001.0,
            af_wtr_id=5001.0,
            sqkm=68800.0,
            name_of_wa='Lake Victoria',
            type_of_wa='Lake',
            shape_area=68800000000.0,
            shape_len=3440000.0,
            geom=MultiPolygon(
                Polygon(((36, -1), (36, 0), (37, 0), (37, -1), (36, -1)))
            )
        )
        self.assertEqual(str(water_body), 'Lake Victoria')
        self.assertEqual(water_body.type_of_wa, 'Lake')
    
    def test_water_body_without_name(self):
        """Test water body string representation without name."""
        water_body = WaterBodies.objects.create(
            fid=1002.0,
            af_wtr_id=5002.0,
            sqkm=100.0,
            shape_area=100000000.0,
            shape_len=40000.0,
            geom=MultiPolygon(
                Polygon(((36, -1), (36, 0), (37, 0), (37, -1), (36, -1)))
            )
        )
        self.assertEqual(str(water_body), 'Water Body 5002.0')


class APITestCase(APITestCase):
    """Test API endpoints."""
    
    def setUp(self):
        # Create test data
        self.test_polygon = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        )
        
        self.affected_pop = AffectedPopulation.objects.create(
            gid_0='KEN',
            name_0='Kenya',
            name_1='Nairobi',
            engtype_1='County',
            lack_cc=0.45,
            cod='KE',
            stock=1000000.0,
            flood_tot=50000.0,
            flood_perc=5.0,
            geom=self.test_polygon
        )
    
    def test_get_affected_population_list(self):
        """Test retrieving list of affected populations."""
        response = self.client.get('/api/v1/affected-population/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'FeatureCollection')
        self.assertEqual(len(response.data['features']), 1)
    
    def test_get_affected_population_detail(self):
        """Test retrieving single affected population."""
        response = self.client.get(f'/api/v1/affected-population/{self.affected_pop.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['properties']['name_1'], 'Nairobi')
    
    def test_filter_affected_population(self):
        """Test filtering affected population by flood percentage."""
        # Create another record with higher flood percentage
        AffectedPopulation.objects.create(
            gid_0='KEN',
            name_0='Kenya',
            name_1='Mombasa',
            engtype_1='County',
            lack_cc=0.5,
            cod='KE',
            stock=800000.0,
            flood_tot=120000.0,
            flood_perc=15.0,
            geom=self.test_polygon
        )
        
        # Filter for high flood percentage
        response = self.client.get('/api/v1/affected-population/?flood_perc__gte=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['features']), 1)
        self.assertEqual(response.data['features'][0]['properties']['name_1'], 'Mombasa')
    
    def test_create_sector_forecast(self):
        """Test creating a sector forecast via API."""
        # First create a sector
        sector = SectorData.objects.create(
            sec_code=10001,
            sec_name='Test Section',
            basin='Test Basin',
            domain='Test Domain',
            admin_b_l1='Test Admin',
            sec_rs='TEST_001',
            area=100.0,
            lat=-1.0,
            lon=36.0,
            q_thr1=50.0,
            q_thr2=100.0,
            q_thr3=150.0,
            geom=Point(36.0, -1.0)
        )
        
        # Create forecast via API
        forecast_data = {
            'sector': sector.id,
            'model_type': 'GFS',
            'time_point': '2024-01-20T12:00:00Z',
            'forecast_value': 75.5
        }
        
        response = self.client.post(
            '/api/v1/sector-forecasts/',
            data=json.dumps(forecast_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SectorForecast.objects.count(), 1)
        
        forecast = SectorForecast.objects.first()
        self.assertEqual(forecast.forecast_value, 75.5)
        self.assertEqual(forecast.model_type, 'GFS')


class RiverSectionModelTest(TestCase):
    """Test RiverSection model."""
    
    def test_river_section_creation(self):
        """Test creating a RiverSection instance."""
        river_section = RiverSection.objects.create(
            section_name='Nairobi River Section A',
            time_restart=datetime(2024, 1, 20, 0, 0),
            time_run=datetime(2024, 1, 20, 6, 0),
            time_start=datetime(2024, 1, 20, 12, 0),
            time_series_discharge_simulated_gfs='[75.5, 82.3, 91.2]',
            time_series_discharge_simulated_icon='[73.2, 80.1, 89.5]',
            time_period='["2024-01-20T12:00:00", "2024-01-20T18:00:00", "2024-01-21T00:00:00"]',
            sec_code=10001,
            sec_name='NRB_001',
            basin='Athi',
            domain='Kenya',
            area=126.5,
            latitude=-1.2921,
            longitude=36.8219,
            q_thr1=50.0,
            q_thr2=100.0,
            q_thr3=150.0,
            category='Medium Risk',
            geometry=Point(36.8219, -1.2921)
        )
        
        self.assertEqual(
            str(river_section), 
            'Nairobi River Section A - 2024-01-20 06:00:00'
        )
        self.assertEqual(river_section.basin, 'Athi')
        self.assertEqual(river_section.category, 'Medium Risk')