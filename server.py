from flask import Flask, request, jsonify
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
from rzd_parser import RZDParser
from avia_parser import AVIAParser
app = Flask(__name__)
CORS(app)
@app.route('/api/search_tickets', methods=['POST'])
def search_tickets():
    data = request.get_json()
    city_from = data.get('city_from')
    city_to = data.get('city_to')
    travel_date = data.get('travel_date')
    def run_parser(parser_class):
        parser = parser_class(city_from, city_to, travel_date)
        return parser.run()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_rzd = executor.submit(run_parser, RZDParser)
        future_avia = executor.submit(run_parser, AVIAParser)

        trains = future_rzd.result()
        flights = future_avia.result()

    return jsonify({
        "status": "success",
        "trains": trains,
        "flights": flights
    })


if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5000)