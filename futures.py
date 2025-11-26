import requests
import json
from datetime import datetime

# Базовый URL для Futures API
BASE_URL = "https://contract.mexc.com/api/v1"


def save_high_funding_futures(filename="high_funding_futures.json"):
    try:
        # Получаем данные по всем контрактам
        response = requests.get(f"{BASE_URL}/contract/ticker")
        data = response.json()

        # Фильтруем контракты с фандингом выше 0.00009
        high_funding_contracts = []
        for contract in data['data']:
            funding_rate = float(contract['fundingRate'])
            if funding_rate > 0.00009:
                high_funding_contracts.append({
                    'symbol': contract['symbol'],
                    'price': contract['lastPrice'],
                    'fundingRate': contract['fundingRate']
                })

        # Создаем структуру для сохранения
        save_data = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "MEXC Futures API",
            "funding_threshold": 0.00009,
            "total_contracts": len(high_funding_contracts),
            "contracts": high_funding_contracts
        }

        # Сохраняем в JSON файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

        return save_data

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


# Запуск
if __name__ == "__main__":
    save_high_funding_futures()