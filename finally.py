import requests
import json
from datetime import datetime


def compare_prices_and_save():
    try:
        # Загружаем данные из файлов
        with open('high_funding_futures.json', 'r', encoding='utf-8') as f:
            futures_data = json.load(f)

        with open('all_spot_prices.json', 'r', encoding='utf-8') as f:
            spot_data = json.load(f)

        # Создаем словарь спотовых цен для быстрого поиска
        spot_prices = {}
        for item in spot_data['prices']:
            # Добавляем проверку на нулевую цену
            price = float(item['price'])
            if price > 0:  # Игнорируем нулевые цены
                spot_prices[item['symbol']] = price

        # Фильтруем фьючерсы с разницей цен более 0.4%
        results = []
        for contract in futures_data['contracts']:
            # Преобразуем формат символа (BTC_USDT -> BTCUSDT)
            spot_symbol = contract['symbol'].replace('_', '')

            if spot_symbol in spot_prices:
                future_price = float(contract['price'])
                spot_price = spot_prices[spot_symbol]

                # Проверяем, что спотовая цена не нулевая (дополнительная защита)
                if spot_price == 0:
                    print(f"Пропуск {contract['symbol']}: спотовая цена равна нулю")
                    continue

                # Вычисляем разницу в процентах
                price_diff_percent = ((future_price - spot_price) / spot_price) * 100

                # Если разница более 0.4%
                if price_diff_percent > 0.4:
                    # Генерируем ссылки с форматом symbol_usdt для обеих
                    spot_url = f"https://www.mexc.com/ru-RU/exchange/{contract['symbol']}"
                    futures_url = f"https://www.mexc.com/futures/{contract['symbol']}"

                    results.append({
                        'symbol': contract['symbol'],
                        'spot_symbol': spot_symbol,  # Добавляем спотовый символ для удобства
                        'future_price': contract['price'],
                        'spot_price': spot_price,
                        'funding_rate': contract['fundingRate'],
                        'price_difference_percent': round(price_diff_percent, 4),
                        'links': {
                            'spot_trading': spot_url,
                            'futures_trading': futures_url
                        }
                    })

        # Сортируем результаты по убыванию разницы в процентах
        results.sort(key=lambda x: x['price_difference_percent'], reverse=True)

        # Создаем структуру для сохранения
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "comparison_threshold": 0.4,
            "total_matches": len(results),
            "data": results
        }

        # Сохраняем в JSON файл
        with open('price_comparison_results.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return output_data

    except Exception as e:
        print(f"Ошибка: {e}")
        return None


# Запуск
if __name__ == "__main__":
    compare_prices_and_save()