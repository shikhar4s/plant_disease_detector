"""Conservative offline care guidance; never infer severity or prescribe chemical doses."""
LANGUAGES = {
    'en': {
        'intro': 'Built-in care guide (AI chat is unavailable). ',
        'healthy': 'The model matched a healthy leaf class. Check the whole plant for symptoms; a leaf photo cannot rule out other problems.',
        'disease': 'This is a possible match, not a confirmed diagnosis. Check other leaves and contact a local agricultural extension service if symptoms spread.',
        'uncertain': 'The model is uncertain. Retake a sharp photo of one leaf in daylight with a plain background.',
        'tips': ['Water at soil level and avoid leaving foliage wet.', 'Keep space between plants for airflow.', 'Clean tools between plants.', 'Monitor new growth and photograph changes.'],
        'recovery': 'Cannot be estimated from a photo',
        'watering': 'Check soil moisture before watering. Let excess water drain; avoid a fixed schedule that keeps roots constantly wet.',
        'upload': 'Use Upload & Analyze, then choose one clear JPEG, PNG or WebP leaf photo under 10 MB. Find saved results in History.',
        'scope': 'I can help with plant care, watering and using PlantDoc. Ask about one of those topics or open a saved result for its care guide.',
    },
    'hi': {
        'intro': 'अंतर्निहित देखभाल मार्गदर्शिका (AI चैट उपलब्ध नहीं है)। ',
        'healthy': 'मॉडल ने स्वस्थ पत्ती की श्रेणी चुनी है। पूरे पौधे में लक्षण देखें; एक फोटो सभी समस्याओं को नहीं बता सकती।',
        'disease': 'यह संभावित पहचान है, निश्चित निदान नहीं। अन्य पत्तियाँ जाँचें और लक्षण फैलने पर स्थानीय कृषि विशेषज्ञ से संपर्क करें।',
        'uncertain': 'मॉडल निश्चित नहीं है। दिन की रोशनी में सादे बैकग्राउंड पर एक पत्ती की साफ फोटो लें।',
        'tips': ['पानी मिट्टी में दें; पत्तियाँ देर तक गीली न रखें।', 'हवा के लिए पौधों में दूरी रखें।', 'पौधे बदलते समय औजार साफ करें।', 'नई पत्तियों को देखें और बदलाव की फोटो लें।'],
        'recovery': 'फोटो से समय का अनुमान नहीं लगाया जा सकता',
        'watering': 'पानी देने से पहले मिट्टी की नमी देखें। अतिरिक्त पानी निकलने दें; जड़ों को लगातार गीला न रखें।',
        'upload': 'Upload & Analyze में 10 MB से छोटी JPEG, PNG या WebP पत्ती की फोटो चुनें। पुराने परिणाम History में मिलेंगे।',
        'scope': 'मैं पौधों की देखभाल, पानी देने और PlantDoc इस्तेमाल करने की जानकारी दे सकता हूँ। देखभाल के लिए पुराना परिणाम भी खोल सकते हैं।',
    },
    'es': {
        'intro': 'Guía integrada de cuidado (chat de IA no disponible). ',
        'healthy': 'El modelo seleccionó una clase de hoja sana. Revise toda la planta; una foto no descarta otros problemas.',
        'disease': 'Es una coincidencia posible, no un diagnóstico confirmado. Revise otras hojas y consulte a un servicio agrícola local si los síntomas se extienden.',
        'uncertain': 'El modelo no está seguro. Tome una foto nítida de una hoja con luz natural y fondo sencillo.',
        'tips': ['Riegue a nivel del suelo y evite mantener las hojas mojadas.', 'Separe las plantas para permitir circulación de aire.', 'Limpie las herramientas entre plantas.', 'Observe el crecimiento nuevo y fotografíe los cambios.'],
        'recovery': 'No se puede estimar con una foto',
        'watering': 'Compruebe la humedad del suelo antes de regar. Deje drenar el exceso de agua y evite mantener las raíces siempre mojadas.',
        'upload': 'En Upload & Analyze elija una foto JPEG, PNG o WebP de una hoja de menos de 10 MB. Los resultados guardados están en History.',
        'scope': 'Puedo ayudar con el cuidado de plantas, el riego y el uso de PlantDoc. Abra un resultado guardado para ver su guía de cuidado.',
    },
    'fr': {
        'intro': 'Guide de soins intégré (chat IA indisponible). ',
        'healthy': 'Le modèle a choisi une classe de feuille saine. Examinez toute la plante ; une photo ne permet pas d’écarter tous les problèmes.',
        'disease': 'Il s’agit d’une correspondance possible, pas d’un diagnostic confirmé. Vérifiez les autres feuilles et consultez un service agricole local si les symptômes se propagent.',
        'uncertain': 'Le modèle est incertain. Reprenez une photo nette d’une feuille à la lumière naturelle sur fond simple.',
        'tips': ['Arrosez au niveau du sol sans laisser le feuillage mouillé.', 'Espacez les plantes pour favoriser la circulation d’air.', 'Nettoyez les outils entre les plantes.', 'Surveillez les nouvelles pousses et photographiez les changements.'],
        'recovery': 'Impossible à estimer à partir d’une photo',
        'watering': 'Vérifiez l’humidité du sol avant d’arroser. Laissez l’excès d’eau s’écouler et évitez de garder les racines constamment humides.',
        'upload': 'Dans Upload & Analyze, choisissez une photo de feuille JPEG, PNG ou WebP de moins de 10 Mo. Retrouvez les résultats dans History.',
        'scope': 'Je peux aider avec les soins des plantes, l’arrosage et PlantDoc. Ouvrez un résultat enregistré pour consulter son guide de soins.',
    },
}


def language_code(language):
    code = (language or 'en').split('-')[0].lower()
    return code if code in LANGUAGES else 'en'


def care_info(disease_name, language='en', uncertain=False):
    text = LANGUAGES[language_code(language)]
    category = 'uncertain' if uncertain else 'healthy' if disease_name.lower().endswith('___healthy') else 'disease'
    return {'recommended_treatment': text[category], 'prevention_tips': text['tips'],
            'expected_recovery_time': text['recovery'], 'guidance_source': 'care-guide'}


def offline_reply(message, language='en', analysis=None):
    text = LANGUAGES[language_code(language)]
    message = message.lower()
    if analysis:
        reply = care_info(analysis.disease_name, language, analysis.confidence < 0.7)['recommended_treatment']
    elif any(term in message for term in ['water', 'पानी', 'riego', 'regar', 'arros']):
        reply = text['watering']
    elif any(term in message for term in ['upload', 'photo', 'फोटो', 'subir', 'télécharg']):
        reply = text['upload']
    else:
        reply = text['scope']
    return text['intro'] + reply
