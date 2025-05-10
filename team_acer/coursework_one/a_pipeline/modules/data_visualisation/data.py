from flask import Flask, render_template, request, jsonify
import pandas as pd
import psycopg2

app = Flask(__name__)

# PostgreSQL Configuration
DB_HOST = "localhost"
DB_PORT = "5439"
DB_NAME = "fift"
DB_USER = "postgres"
DB_PASSWORD = "postgres"

# Load Data from PostgreSQL
def load_data_from_postgres():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER,
            password=DB_PASSWORD
        )
        df = pd.read_sql_query("SELECT * FROM csr_indicators", conn)
        conn.close()
        df['symbol'] = df['symbol'].str.strip()
        df['year'] = df['year'].astype(int)
        print("✅ Data loaded from PostgreSQL!")
        return df
    except Exception as e:
        print("❌ Failed to load data from PostgreSQL:", str(e))
        return pd.DataFrame()

df = load_data_from_postgres()

ALL_INDICATORS = {
    'water_consumption': ('water_consumption_mcm', 'Water Consumption (MCM)'),
    'total_emissions': ('total_emissions', 'Total Emissions'),
    'donation': ('donation', 'Donations'),
    'waste_generated': ('waste_generated_tons', 'Waste Generated (tons)'),
    'renewable_energy_amount': ('renewable_energy_amount_mwh', 'Renewable Energy (MWh)'),
    'renewable_energy_percentage': ('renewable_energy_percentage', 'Renewable Energy (%)'),
    'air_emissions_nox': ('air_emissions_nox', 'NOx Emissions'),
    'air_emissions_sox': ('air_emissions_sox', 'SOx Emissions'),
    'air_emissions_voc': ('air_emissions_voc', 'VOC Emissions')
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search_data():
    try:
        term = request.args.get('term', '').strip().lower()
        search_type = request.args.get('type', 'symbol').strip().lower()
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        indicators = request.args.getlist('indicators[]')

        if not term:
            return jsonify({'error': 'Search term is required'}), 400

        if search_type not in df.columns:
            return jsonify({'error': f'Invalid search type: {search_type}'}), 400

        filtered_df = df[df[search_type].str.lower().str.contains(term)]

        if start_year:
            filtered_df = filtered_df[filtered_df['year'] >= start_year]
        if end_year:
            filtered_df = filtered_df[filtered_df['year'] <= end_year]

        if filtered_df.empty:
            return jsonify({'error': f'No results found for "{term}"'}), 404

        filtered_df = filtered_df.sort_values('year').fillna(0)

        response = {
            'year': filtered_df['year'].tolist(),
            'company_info': {
                'name': filtered_df['security'].iloc[0],
                'symbol': filtered_df['symbol'].iloc[0],
                'sector': filtered_df['sector'].iloc[0],
                'industry': filtered_df['industry'].iloc[0],
                'region': filtered_df['region'].iloc[0],
                'country': filtered_df['country'].iloc[0]
            },
            'available_indicators': list(ALL_INDICATORS.keys()),
            'indicator_labels': {k: v[1] for k, v in ALL_INDICATORS.items()}
        }

        for key, (col, _) in ALL_INDICATORS.items():
            if not indicators or key in indicators:
                response[key] = filtered_df[col].tolist()

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/sector_analysis')
def sector_analysis():
    try:
        analysis_type = request.args.get('type', 'total')
        entity = request.args.get('entity', 'sector')

        if entity not in ['sector', 'industry', 'region']:
            return jsonify({'error': f'Invalid entity: {entity}'}), 400

        group = df.groupby(entity)

        if analysis_type == 'total':
            result = group['water_consumption_mcm'].sum().sort_values(ascending=False)
            return jsonify({entity: {
                'names': result.index.tolist(),
                'values': result.values.tolist()
            }})
        else:
            stats = group['water_consumption_mcm'].agg(['mean', 'median', 'std']).dropna()
            return jsonify({entity: {
                'names': stats.index.tolist(),
                'mean': stats['mean'].tolist(),
                'median': stats['median'].tolist(),
                'std': stats['std'].tolist()
            }})

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/yearly_heatmap')
def yearly_heatmap():
    try:
        type_ = request.args.get('type', 'industry')
        if type_ not in ['sector', 'industry', 'region']:
            return jsonify({'error': f'Invalid type: {type_}'}), 400

        pivot = df.pivot_table(index=type_, columns='year', values='water_consumption_mcm', aggfunc='mean').fillna(0)
        pivot = pivot.sort_index()

        return jsonify({
            'x': pivot.columns.tolist(),
            'y': pivot.index.tolist(),
            'z': pivot.values.tolist()
        })
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def handle_average_query(group_col):
    try:
        value = request.args.get(group_col, '').strip()
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)
        indicators = request.args.getlist('indicators[]')

        if not value:
            return jsonify({'error': f'{group_col.title()} is required'}), 400

        filtered_df = df[df[group_col].str.lower() == value.lower()]
        if start_year:
            filtered_df = filtered_df[filtered_df['year'] >= start_year]
        if end_year:
            filtered_df = filtered_df[filtered_df['year'] <= end_year]

        if filtered_df.empty:
            return jsonify({'error': f'No data found for {group_col} = {value}'}), 404

        grouped = filtered_df.groupby('year').mean(numeric_only=True).reset_index()
        result = {'year': grouped['year'].tolist()}

        for key, (col, _) in ALL_INDICATORS.items():
            if not indicators or key in indicators:
                result[key] = grouped[col].fillna(0).tolist()

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/region')
def average_by_region():
    return handle_average_query('region')

@app.route('/sector')
def average_by_sector():
    return handle_average_query('sector')

@app.route('/industry')
def average_by_industry():
    return handle_average_query('industry')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)