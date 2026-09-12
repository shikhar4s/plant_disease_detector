"""Versioned class parsing and conservative, non-prescriptive disease information."""
from .model_service import display_name

DISCLAIMER = (
    'PlantDoc provides a model-based suggestion, not a guaranteed diagnosis. For serious or spreading crop '
    'problems, consult a qualified agricultural expert before applying crop-protection products.'
)
DISCLAIMER_HI = ('PlantDoc मॉडल-आधारित सुझाव देता है, पक्का निदान नहीं। गंभीर या फैलती समस्या में '
                 'फसल-सुरक्षा उत्पाद लगाने से पहले योग्य कृषि विशेषज्ञ से सलाह लें।')

DETAILS = {
    'healthy': {
        'symptoms': ['No class-specific disease pattern was identified by this classifier.'],
        'causes': ['The image most closely matched a healthy class; hidden or unsupported problems remain possible.'],
        'actions': ['Inspect the whole plant and nearby plants.', 'Continue crop-appropriate watering and nutrition.'],
        'prevention': ['Keep tools clean.', 'Monitor new growth and record changes.'],
    },
    'bacterial spot': {
        'symptoms': ['Small dark or water-soaked leaf spots that may develop pale margins.'],
        'causes': ['Bacterial infection favoured by wet foliage and splash dispersal.'],
        'actions': ['Remove badly affected material where locally recommended.', 'Avoid handling wet plants and seek local crop advice.'],
        'prevention': ['Use clean seed or transplants.', 'Reduce leaf wetness and disinfect tools.'],
    },
    'early blight': {
        'symptoms': ['Brown lesions that may show concentric rings, often beginning on older leaves.'],
        'causes': ['Fungal infection favoured by warm, humid conditions and prolonged leaf wetness.'],
        'actions': ['Remove heavily affected leaves if safe for the crop.', 'Improve airflow and obtain local treatment advice.'],
        'prevention': ['Rotate susceptible crops.', 'Water at soil level and clear infected residue.'],
    },
    'late blight': {
        'symptoms': ['Rapidly enlarging dark, water-soaked lesions; pale growth may appear beneath leaves in humid weather.'],
        'causes': ['Oomycete infection favoured by cool, wet conditions.'],
        'actions': ['Isolate and inspect plants promptly.', 'Contact an agricultural expert because outbreaks can spread rapidly.'],
        'prevention': ['Use clean planting material.', 'Limit prolonged leaf wetness and monitor during cool, humid periods.'],
    },
    'powdery mildew': {
        'symptoms': ['White powder-like growth on leaves, sometimes with curling or yellowing.'],
        'causes': ['Fungal growth favoured by susceptible crops, dense canopies and suitable humidity.'],
        'actions': ['Improve airflow and remove severely affected tissue where appropriate.', 'Confirm locally before treatment.'],
        'prevention': ['Avoid overcrowding.', 'Use resistant varieties where available.'],
    },
    'rust': {
        'symptoms': ['Orange, yellow or brown powdery pustules on leaf surfaces.'],
        'causes': ['Rust fungi spread by airborne spores under favourable moisture and temperature.'],
        'actions': ['Inspect both leaf surfaces and nearby plants.', 'Seek crop-specific local guidance.'],
        'prevention': ['Remove volunteer hosts where recommended.', 'Use resistant varieties and maintain airflow.'],
    },
    'leaf spot': {
        'symptoms': ['Discrete brown, black or grey spots that may merge as tissue dies.'],
        'causes': ['Several fungal or bacterial agents can cause similar-looking leaf spots.'],
        'actions': ['Photograph both leaf surfaces and monitor spread.', 'Use laboratory or expert confirmation for serious cases.'],
        'prevention': ['Avoid overhead irrigation when practical.', 'Sanitise tools and manage infected residue.'],
    },
    'virus': {
        'symptoms': ['Mottling, mosaic colour, curling, distortion or stunted growth may occur.'],
        'causes': ['A plant virus, sometimes spread by vectors such as aphids or whiteflies.'],
        'actions': ['Inspect for insect vectors and isolate suspect plants.', 'Seek expert confirmation; viral symptoms can resemble nutrient or herbicide injury.'],
        'prevention': ['Use clean planting material.', 'Manage vectors using locally approved integrated practices.'],
    },
}

DETAILS_HI = {
    'healthy': {
        'symptoms': ['इस वर्गीकारक को कोई खास रोग पैटर्न नहीं मिला।'],
        'causes': ['छवि स्वस्थ वर्ग से सबसे अधिक मिली; छिपी या मॉडल से बाहर की समस्या फिर भी संभव है।'],
        'actions': ['पूरे पौधे और पास के पौधों को देखें।', 'फसल के अनुसार पानी और पोषण जारी रखें।'],
        'prevention': ['औजार साफ रखें।', 'नई बढ़त देखें और बदलाव दर्ज करें।'],
    },
    'bacterial spot': {
        'symptoms': ['छोटे गहरे या पानी से भीगे जैसे धब्बे, जिनके किनारे हल्के हो सकते हैं।'],
        'causes': ['गीली पत्तियों और पानी की छींटों से फैलने वाला संभावित जीवाणु संक्रमण।'],
        'actions': ['स्थानीय सलाह के अनुसार बहुत प्रभावित भाग हटाएँ।', 'गीले पौधों को न छुएँ और स्थानीय कृषि सलाह लें।'],
        'prevention': ['स्वच्छ बीज या पौध इस्तेमाल करें।', 'पत्तियों की नमी घटाएँ और औजार साफ करें।'],
    },
    'early blight': {
        'symptoms': ['भूरे घाव जिनमें गोल छल्ले हो सकते हैं और जो अक्सर पुरानी पत्तियों पर पहले दिखते हैं।'],
        'causes': ['गर्म, नम मौसम और लंबे समय तक गीली पत्तियों से अनुकूल संभावित फफूंद संक्रमण।'],
        'actions': ['फसल के लिए सुरक्षित हो तो बहुत प्रभावित पत्तियाँ हटाएँ।', 'हवा का प्रवाह बढ़ाएँ और स्थानीय उपचार सलाह लें।'],
        'prevention': ['संवेदनशील फसलों का चक्र बदलें।', 'मिट्टी के स्तर पर पानी दें और संक्रमित अवशेष हटाएँ।'],
    },
    'late blight': {
        'symptoms': ['तेजी से बढ़ते गहरे, पानी से भीगे जैसे घाव; नम मौसम में पत्ती के नीचे हल्की वृद्धि दिख सकती है।'],
        'causes': ['ठंडे और गीले मौसम से अनुकूल संभावित ऊमाइसीट संक्रमण।'],
        'actions': ['पौधों को अलग करके तुरंत जाँचें।', 'यह तेजी से फैल सकता है, इसलिए कृषि विशेषज्ञ से संपर्क करें।'],
        'prevention': ['स्वच्छ रोपण सामग्री लें।', 'लंबी पत्ती-नमी घटाएँ और ठंडे नम समय में निगरानी करें।'],
    },
    'powdery mildew': {
        'symptoms': ['पत्तियों पर सफेद चूर्ण जैसा आवरण, कभी-कभी मुड़ना या पीलापन।'],
        'causes': ['संवेदनशील फसल, घना छत्र और अनुकूल आर्द्रता से बढ़ने वाली संभावित फफूंद।'],
        'actions': ['हवा का प्रवाह बढ़ाएँ और उचित हो तो बहुत प्रभावित भाग हटाएँ।', 'उपचार से पहले स्थानीय पुष्टि लें।'],
        'prevention': ['बहुत घना रोपण न करें।', 'जहाँ उपलब्ध हो प्रतिरोधी किस्म लें।'],
    },
    'rust': {
        'symptoms': ['पत्ती पर नारंगी, पीले या भूरे चूर्ण जैसे दाने।'],
        'causes': ['अनुकूल नमी और तापमान में हवा से फैलने वाली संभावित रस्ट फफूंद।'],
        'actions': ['पत्ती की दोनों सतह और पास के पौधे देखें।', 'फसल-विशेष स्थानीय सलाह लें।'],
        'prevention': ['स्थानीय सलाह पर वैकल्पिक पोषक पौधे हटाएँ।', 'प्रतिरोधी किस्म और अच्छा वायु प्रवाह रखें।'],
    },
    'leaf spot': {
        'symptoms': ['भूरे, काले या धूसर अलग धब्बे जो ऊतक मरने पर मिल सकते हैं।'],
        'causes': ['कई फफूंद या जीवाणु एक जैसे पत्ती-धब्बे बना सकते हैं।'],
        'actions': ['पत्ती की दोनों सतह की फोटो लें और फैलाव देखें।', 'गंभीर स्थिति में प्रयोगशाला या विशेषज्ञ पुष्टि लें।'],
        'prevention': ['संभव हो तो ऊपर से सिंचाई न करें।', 'औजार साफ करें और संक्रमित अवशेष संभालें।'],
    },
    'virus': {
        'symptoms': ['चितकबरापन, मोज़ेक रंग, मुड़ना, विकृति या रुकी बढ़त हो सकती है।'],
        'causes': ['संभावित पौध वायरस, जो माहू या सफेद मक्खी जैसे वाहकों से फैल सकता है।'],
        'actions': ['कीट वाहक देखें और संदिग्ध पौधे अलग करें।', 'विशेषज्ञ पुष्टि लें; पोषण या शाकनाशी क्षति भी ऐसी दिख सकती है।'],
        'prevention': ['स्वच्छ रोपण सामग्री लें।', 'स्थानीय रूप से स्वीकृत समेकित तरीकों से वाहक नियंत्रित करें।'],
    },
}


def split_label(label):
    crop, condition = label.split('___', 1) if '___' in label else ('Unknown crop', label)
    return crop.replace('_', ' ').replace(',', '').strip(), condition.replace('_', ' ').strip()


def disease_info(label, uncertain=False, language='en'):
    crop, condition = split_label(label)
    key = condition.lower()
    hindi = str(language).lower().startswith('hi')
    if uncertain:
        details = ({
            'symptoms': ['इस छवि से भरोसेमंद लक्षण-मिलान नहीं बताया जा सकता।'],
            'causes': ['छवि अस्पष्ट, असंबंधित, मॉडल से बाहर या संदिग्ध हो सकती है।'],
            'actions': ['दिन की रोशनी में सादे बैकग्राउंड पर एक पत्ती की साफ फोटो लें।', 'फसल बिगड़ रही हो तो कृषि विशेषज्ञ से संपर्क करें।'],
            'prevention': ['फसल देखें और तारीख सहित बदलाव दर्ज करें।'],
        } if hindi else {
            'symptoms': ['No reliable symptom match can be reported from this image.'],
            'causes': ['The image may be unclear, unrelated, unsupported, or ambiguous for this model.'],
            'actions': ['Upload a sharper photo of one leaf in daylight on a plain background.', 'Consult an agricultural expert if the crop is deteriorating.'],
            'prevention': ['Monitor the crop and keep a dated record of changes.'],
        })
    else:
        match = next((name for name in DETAILS if name in key), 'healthy' if key == 'healthy' else 'leaf spot')
        details = (DETAILS_HI if hindi else DETAILS)[match]
    return {'crop': crop, 'disease': condition, 'display_name': display_name(label), **details,
            'disclaimer': DISCLAIMER_HI if hindi else DISCLAIMER}
