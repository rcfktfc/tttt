import requests
import json
from datetime import datetime


def save_all_spot_prices(filename="all_spot_prices.json"):
    """Получает все спотовые пары с ценами и сохраняет в JSON"""
    try:
        # Делаем запрос к API
        response = requests.get("https://api.mexc.com/api/v3/ticker/price")
        data = response.json()

        # Формируем структуру данных с временной меткой
        result = {
            "timestamp": datetime.now().isoformat(),
            "data_source": "MEXC Spot API",
            "total_pairs": len(data),
            "prices": data
        }

        # Сохраняем в JSON файл
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Успешно сохранено {len(data)} торговых пар в файл: {filename}")
        return result

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


# Запускаем
if __name__ == "__main__":
    save_all_spot_prices()