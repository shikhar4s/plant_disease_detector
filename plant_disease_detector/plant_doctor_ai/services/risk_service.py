"""Transparent weather-favourability heuristic; not a validated disease prediction."""

REFERENCES = [
    {'title': 'APS disease triangle', 'url': 'https://www.apsnet.org/edcenter/learningPP/Pages/DiseaseTriangle.aspx'},
    {'title': 'APS review of leaf wetness and plant disease',
     'url': 'https://apsjournals.apsnet.org/doi/10.1094/PDIS-05-14-0529-FE'},
]


def weather_risk(weather, crop='', disease='', language='en'):
    current = (weather or {}).get('current') or {}
    forecast = (weather or {}).get('forecast') or []
    humidity = current.get('relative_humidity_2m')
    temperature = current.get('temperature_2m')
    rain_probability = max((d.get('precipitation_probability_max') or 0 for d in forecast[:3]), default=0)
    precipitation = sum((d.get('precipitation_sum') or 0 for d in forecast[:3]))
    if humidity is None or temperature is None:
        hindi = str(language).lower().startswith('hi')
        return {'level': 'Unavailable', 'score': None,
                'reasons': ['आर्द्रता या तापमान का डेटा उपलब्ध नहीं है।' if hindi else
                            'Humidity or temperature data is missing.'],
                'method': ('यह पारदर्शी मौसम-अनुकूलता नियम है; यह प्रमाणित रोग पूर्वानुमान नहीं है।' if hindi else
                           'Transparent weather-favourability heuristic; not a validated disease prediction.'),
                'references': REFERENCES}
    hindi = str(language).lower().startswith('hi')
    score, reasons = 0, []
    if humidity >= 80:
        score += 2; reasons.append((f'अधिक आर्द्रता ({humidity}%) पत्तियों को लंबे समय तक गीला रख सकती है।' if hindi else
                                    f'High humidity ({humidity}%) can prolong leaf wetness.'))
    elif humidity >= 65:
        score += 1; reasons.append((f'मध्यम से अधिक आर्द्रता ({humidity}%) कुछ पत्ती रोगों के अनुकूल हो सकती है।' if hindi else
                                    f'Moderate-to-high humidity ({humidity}%) may favour some foliar diseases.'))
    if rain_probability >= 60 or precipitation >= 5:
        score += 2; reasons.append((f'बारिश की संभावना है ({rain_probability}% अधिकतम; 3 दिनों में {precipitation:.1f} मिमी)।' if hindi else
                                    f'Rain is likely or forecast ({rain_probability}% peak; {precipitation:.1f} mm over 3 days).'))
    if 18 <= temperature <= 30 and humidity >= 65:
        score += 1; reasons.append((f'तापमान ({temperature}°C) और आर्द्रता कई रोगजनकों के अनुकूल हो सकते हैं।' if hindi else
                                    f'Temperature ({temperature}°C) plus humidity may suit several pathogens.'))
    if temperature >= 35:
        reasons.append((f'गर्मी ({temperature}°C) फसल पर दबाव डाल सकती है; रोग जोखिम से अलग मिट्टी की नमी देखें।' if hindi else
                        f'Heat ({temperature}°C) may stress crops; monitor soil moisture separately from disease risk.'))
    level = 'High' if score >= 4 else 'Moderate' if score >= 2 else 'Low'
    level_label = {'High': 'उच्च', 'Moderate': 'मध्यम', 'Low': 'कम'}[level] if hindi else level
    return {'level': level, 'level_label': level_label, 'score': score, 'crop': crop or None,
            'disease_context': disease or None,
            'reasons': reasons or [('वर्तमान मौसम तय आर्द्रता/बारिश नियमों को सक्रिय नहीं करता।' if hindi else
                                    'Current weather does not trigger the configured humidity/rain rules.')],
            'method': ('यह केवल नियम-आधारित मौसम अनुकूलता है; यह संक्रमण का निदान या गंभीरता नहीं बताती।' if hindi else
                       'Rule-based weather favourability only; it does not diagnose infection or measure severity.'),
            'rules_version': 'weather-risk-v1', 'references': REFERENCES}
