import i18n from 'i18next';
import { featureTranslations } from './features';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  en: {
    translation: {
      "app": {
        "title": "PlantDoc",
        "subtitle": "AI-Powered Plant Disease Detection"
      },
      "auth": {
        "login": {
          "title": "Welcome Back",
          "subtitle": "Sign in to your account",
          "email": "Email Address",
          "password": "Password",
          "emailPlaceholder": "Enter your email",
          "passwordPlaceholder": "Enter your password",
          "signIn": "Sign In",
          "signingIn": "Signing in...",
          "noAccount": "Don't have an account?",
          "signUp": "Sign up"
        },
        "signup": {
          "title": "Create Account",
          "subtitle": "Join PlantDoc today",
          "name": "Full Name",
          "email": "Email Address",
          "password": "Password",
          "confirmPassword": "Confirm Password",
          "namePlaceholder": "Enter your full name",
          "emailPlaceholder": "Enter your email",
          "passwordPlaceholder": "Enter your password",
          "confirmPasswordPlaceholder": "Confirm your password",
          "createAccount": "Create Account",
          "creatingAccount": "Creating Account...",
          "haveAccount": "Already have an account?",
          "signIn": "Sign in"
        }
      },
      "dashboard": {
        "sidebar": {
          "upload": "Upload Image",
          "history": "History",
          "analytics": "Analytics",
          "profile": "Profile",
          "contact": "Contact Us",
          "logout": "Logout"
        },
        "upload": {
          "title": "Plant Disease Detection",
          "subtitle": "Upload an image of your plant to detect diseases and get treatment recommendations",
          "dropZone": "Drop your plant image here",
          "browseText": "or click to browse from your computer",
          "supportedFormats": "Supports: JPG, PNG, JPEG (Max 10MB)",
          "chooseFile": "Choose File",
          "analyzing": "Analyzing Image...",
          "analyzingSubtext": "Our AI is examining your plant for diseases",
          "noAnalysis": "No Analysis Yet",
          "noAnalysisSubtext": "Upload a plant image to see detection results"
        },
        "history": {
          "title": "Upload History",
          "subtitle": "View your previous plant disease analysis results",
          "noHistory": "No History Yet",
          "noHistorySubtext": "Start uploading plant images to see your analysis history",
          "view": "View",
          "severity": "Severity"
        },
        "analytics": {
          "title": "Analytics Dashboard",
          "subtitle": "Insights from your plant disease detection history",
          "noData": "No Data Available",
          "noDataSubtext": "Upload and analyze plant images to see your analytics",
          "totalUploads": "Total Uploads",
          "analyzed": "Analyzed",
          "successRate": "Success Rate",
          "avgConfidence": "Avg Confidence",
          "diseaseDistribution": "Disease Distribution",
          "severityDistribution": "Severity Distribution"
        },
        "profile": {
          "title": "Profile Settings",
          "subtitle": "Manage your account information and preferences",
          "personalInfo": "Personal Information",
          "editProfile": "Edit Profile",
          "save": "Save",
          "cancel": "Cancel",
          "changePhoto": "Change Photo",
          "fullName": "Full Name",
          "emailAddress": "Email Address",
          "signOut": "Sign Out",
          "accountStats": "Account Stats",
          "memberSince": "Member Since",
          "preferences": "Preferences",
          "emailNotifications": "Email Notifications",
          "analysisAlerts": "Analysis Alerts",
          "monthlyReports": "Monthly Reports"
        },
        "contact": {
          "title": "Contact Our Team",
          "subtitle": "Get in touch with our development team",
          "teamMembers": "Team Members",
          "contact": "Contact",
          "getInTouch": "Get in Touch",
          "getInTouchSubtext": "Have questions or feedback? We'd love to hear from you!"
        }
      },
      "result": {
        "title": "Analysis Results",
        "severity": "Severity",
        "confidence": "Confidence",
        "recoveryTime": "Expected recovery time",
        "treatment": "Recommended Treatment",
        "prevention": "Prevention Tips",
        "gotIt": "Got it, thanks!"
      },
      "chatbot": {
        "title": "AI Assistant",
        "subtitle": "Farming & Plant Care Expert",
        "placeholder": "Ask about plant care...",
        "greeting": "Hello! I'm your AI farming assistant. I can help you with plant disease diagnosis, treatment recommendations, and general farming advice. How can I assist you today?"
      },
      "common": {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "call": "Call",
        "sms": "SMS"
      }
    }
  },
  hi: {
    translation: {
      "app": {
        "title": "प्लांटडॉक",
        "subtitle": "AI-संचालित पौधे रोग पहचान"
      },
      "auth": {
        "login": {
          "title": "वापस स्वागत है",
          "subtitle": "अपने खाते में साइन इन करें",
          "email": "ईमेल पता",
          "password": "पासवर्ड",
          "emailPlaceholder": "अपना ईमेल दर्ज करें",
          "passwordPlaceholder": "अपना पासवर्ड दर्ज करें",
          "signIn": "साइन इन",
          "signingIn": "साइन इन हो रहा है...",
          "noAccount": "खाता नहीं है?",
          "signUp": "साइन अप करें"
        },
        "signup": {
          "title": "खाता बनाएं",
          "subtitle": "आज ही प्लांटडॉक में शामिल हों",
          "name": "पूरा नाम",
          "email": "ईमेल पता",
          "password": "पासवर्ड",
          "confirmPassword": "पासवर्ड की पुष्टि करें",
          "namePlaceholder": "अपना पूरा नाम दर्ज करें",
          "emailPlaceholder": "अपना ईमेल दर्ज करें",
          "passwordPlaceholder": "अपना पासवर्ड दर्ज करें",
          "confirmPasswordPlaceholder": "अपने पासवर्ड की पुष्टि करें",
          "createAccount": "खाता बनाएं",
          "creatingAccount": "खाता बनाया जा रहा है...",
          "haveAccount": "पहले से खाता है?",
          "signIn": "साइन इन करें"
        }
      },
      "dashboard": {
        "sidebar": {
          "upload": "छवि अपलोड करें",
          "history": "इतिहास",
          "analytics": "विश्लेषण",
          "profile": "प्रोफ़ाइल",
          "contact": "संपर्क करें",
          "logout": "लॉगआउट"
        },
        "upload": {
          "title": "पौधे रोग पहचान",
          "subtitle": "रोगों का पता लगाने और उपचार की सिफारिशें प्राप्त करने के लिए अपने पौधे की छवि अपलोड करें",
          "dropZone": "अपने पौधे की छवि यहाँ छोड़ें",
          "browseText": "या अपने कंप्यूटर से ब्राउज़ करने के लिए क्लिक करें",
          "supportedFormats": "समर्थित: JPG, PNG, JPEG (अधिकतम 10MB)",
          "chooseFile": "फ़ाइल चुनें",
          "analyzing": "छवि का विश्लेषण...",
          "analyzingSubtext": "हमारा AI आपके पौधे की बीमारियों की जांच कर रहा है",
          "noAnalysis": "अभी तक कोई विश्लेषण नहीं",
          "noAnalysisSubtext": "पहचान परिणाम देखने के लिए पौधे की छवि अपलोड करें"
        },
        "history": {
          "title": "अपलोड इतिहास",
          "subtitle": "अपने पिछले पौधे रोग विश्लेषण परिणाम देखें",
          "noHistory": "अभी तक कोई इतिहास नहीं",
          "noHistorySubtext": "अपना विश्लेषण इतिहास देखने के लिए पौधे की छवियां अपलोड करना शुरू करें",
          "view": "देखें",
          "severity": "गंभीरता"
        },
        "analytics": {
          "title": "विश्लेषण डैशबोर्ड",
          "subtitle": "आपके पौधे रोग पहचान इतिहास से अंतर्दृष्टि",
          "noData": "कोई डेटा उपलब्ध नहीं",
          "noDataSubtext": "अपना विश्लेषण देखने के लिए पौधे की छवियां अपलोड और विश्लेषण करें",
          "totalUploads": "कुल अपलोड",
          "analyzed": "विश्लेषित",
          "successRate": "सफलता दर",
          "avgConfidence": "औसत विश्वास",
          "diseaseDistribution": "रोग वितरण",
          "severityDistribution": "गंभीरता वितरण"
        },
        "profile": {
          "title": "प्रोफ़ाइल सेटिंग्स",
          "subtitle": "अपनी खाता जानकारी और प्राथमिकताएं प्रबंधित करें",
          "personalInfo": "व्यक्तिगत जानकारी",
          "editProfile": "प्रोफ़ाइल संपादित करें",
          "save": "सहेजें",
          "cancel": "रद्द करें",
          "changePhoto": "फोटो बदलें",
          "fullName": "पूरा नाम",
          "emailAddress": "ईमेल पता",
          "signOut": "साइन आउट",
          "accountStats": "खाता आंकड़े",
          "memberSince": "सदस्य बने",
          "preferences": "प्राथमिकताएं",
          "emailNotifications": "ईमेल सूचनाएं",
          "analysisAlerts": "विश्लेषण अलर्ट",
          "monthlyReports": "मासिक रिपोर्ट"
        },
        "contact": {
          "title": "हमारी टीम से संपर्क करें",
          "subtitle": "हमारी विकास टीम से संपर्क करें",
          "teamMembers": "टीम सदस्य",
          "contact": "संपर्क",
          "getInTouch": "संपर्क में रहें",
          "getInTouchSubtext": "प्रश्न या फीडबैक है? हम आपसे सुनना पसंद करेंगे!"
        }
      },
      "result": {
        "title": "विश्लेषण परिणाम",
        "severity": "गंभीरता",
        "confidence": "विश्वास",
        "recoveryTime": "अपेक्षित रिकवरी समय",
        "treatment": "अनुशंसित उपचार",
        "prevention": "रोकथाम युक्तियाँ",
        "gotIt": "समझ गया, धन्यवाद!"
      },
      "chatbot": {
        "title": "AI सहायक",
        "subtitle": "कृषि और पौधे देखभाल विशेषज्ञ",
        "placeholder": "पौधे की देखभाल के बारे में पूछें...",
        "greeting": "नमस्ते! मैं आपका AI कृषि सहायक हूं। मैं पौधे रोग निदान, उपचार सिफारिशों और सामान्य कृषि सलाह में आपकी मदद कर सकता हूं। आज मैं आपकी कैसे सहायता कर सकता हूं?"
      },
      "common": {
        "low": "कम",
        "medium": "मध्यम",
        "high": "उच्च",
        "call": "कॉल करें",
        "sms": "SMS"
      }
    }
  },
  es: {
    translation: {
      "app": {
        "title": "PlantDoc",
        "subtitle": "Detección de Enfermedades de Plantas con IA"
      },
      "auth": {
        "login": {
          "title": "Bienvenido de Vuelta",
          "subtitle": "Inicia sesión en tu cuenta",
          "email": "Dirección de Correo",
          "password": "Contraseña",
          "emailPlaceholder": "Ingresa tu correo",
          "passwordPlaceholder": "Ingresa tu contraseña",
          "signIn": "Iniciar Sesión",
          "signingIn": "Iniciando sesión...",
          "noAccount": "¿No tienes cuenta?",
          "signUp": "Regístrate"
        },
        "signup": {
          "title": "Crear Cuenta",
          "subtitle": "Únete a PlantDoc hoy",
          "name": "Nombre Completo",
          "email": "Dirección de Correo",
          "password": "Contraseña",
          "confirmPassword": "Confirmar Contraseña",
          "namePlaceholder": "Ingresa tu nombre completo",
          "emailPlaceholder": "Ingresa tu correo",
          "passwordPlaceholder": "Ingresa tu contraseña",
          "confirmPasswordPlaceholder": "Confirma tu contraseña",
          "createAccount": "Crear Cuenta",
          "creatingAccount": "Creando Cuenta...",
          "haveAccount": "¿Ya tienes cuenta?",
          "signIn": "Iniciar sesión"
        }
      },
      "dashboard": {
        "sidebar": {
          "upload": "Subir Imagen",
          "history": "Historial",
          "analytics": "Análisis",
          "profile": "Perfil",
          "contact": "Contáctanos",
          "logout": "Cerrar Sesión"
        },
        "upload": {
          "title": "Detección de Enfermedades de Plantas",
          "subtitle": "Sube una imagen de tu planta para detectar enfermedades y obtener recomendaciones de tratamiento",
          "dropZone": "Suelta la imagen de tu planta aquí",
          "browseText": "o haz clic para navegar desde tu computadora",
          "supportedFormats": "Soporta: JPG, PNG, JPEG (Máx 10MB)",
          "chooseFile": "Elegir Archivo",
          "analyzing": "Analizando Imagen...",
          "analyzingSubtext": "Nuestra IA está examinando tu planta en busca de enfermedades",
          "noAnalysis": "Sin Análisis Aún",
          "noAnalysisSubtext": "Sube una imagen de planta para ver los resultados de detección"
        },
        "history": {
          "title": "Historial de Subidas",
          "subtitle": "Ve los resultados de análisis previos de enfermedades de plantas",
          "noHistory": "Sin Historial Aún",
          "noHistorySubtext": "Comienza subiendo imágenes de plantas para ver tu historial de análisis",
          "view": "Ver",
          "severity": "Severidad"
        },
        "analytics": {
          "title": "Panel de Análisis",
          "subtitle": "Perspectivas de tu historial de detección de enfermedades de plantas",
          "noData": "No Hay Datos Disponibles",
          "noDataSubtext": "Sube y analiza imágenes de plantas para ver tus análisis",
          "totalUploads": "Subidas Totales",
          "analyzed": "Analizadas",
          "successRate": "Tasa de Éxito",
          "avgConfidence": "Confianza Promedio",
          "diseaseDistribution": "Distribución de Enfermedades",
          "severityDistribution": "Distribución de Severidad"
        },
        "profile": {
          "title": "Configuración de Perfil",
          "subtitle": "Gestiona la información de tu cuenta y preferencias",
          "personalInfo": "Información Personal",
          "editProfile": "Editar Perfil",
          "save": "Guardar",
          "cancel": "Cancelar",
          "changePhoto": "Cambiar Foto",
          "fullName": "Nombre Completo",
          "emailAddress": "Dirección de Correo",
          "signOut": "Cerrar Sesión",
          "accountStats": "Estadísticas de Cuenta",
          "memberSince": "Miembro Desde",
          "preferences": "Preferencias",
          "emailNotifications": "Notificaciones por Correo",
          "analysisAlerts": "Alertas de Análisis",
          "monthlyReports": "Reportes Mensuales"
        },
        "contact": {
          "title": "Contacta a Nuestro Equipo",
          "subtitle": "Ponte en contacto con nuestro equipo de desarrollo",
          "teamMembers": "Miembros del Equipo",
          "contact": "Contacto",
          "getInTouch": "Ponte en Contacto",
          "getInTouchSubtext": "¿Tienes preguntas o comentarios? ¡Nos encantaría escucharte!"
        }
      },
      "result": {
        "title": "Resultados del Análisis",
        "severity": "Severidad",
        "confidence": "Confianza",
        "recoveryTime": "Tiempo de recuperación esperado",
        "treatment": "Tratamiento Recomendado",
        "prevention": "Consejos de Prevención",
        "gotIt": "¡Entendido, gracias!"
      },
      "chatbot": {
        "title": "Asistente IA",
        "subtitle": "Experto en Agricultura y Cuidado de Plantas",
        "placeholder": "Pregunta sobre cuidado de plantas...",
        "greeting": "¡Hola! Soy tu asistente de agricultura IA. Puedo ayudarte con diagnóstico de enfermedades de plantas, recomendaciones de tratamiento y consejos generales de agricultura. ¿Cómo puedo asistirte hoy?"
      },
      "common": {
        "low": "Bajo",
        "medium": "Medio",
        "high": "Alto",
        "call": "Llamar",
        "sms": "SMS"
      }
    }
  },
  fr: {
    translation: {
      "app": {
        "title": "PlantDoc",
        "subtitle": "Détection de Maladies des Plantes par IA"
      },
      "auth": {
        "login": {
          "title": "Bon Retour",
          "subtitle": "Connectez-vous à votre compte",
          "email": "Adresse Email",
          "password": "Mot de Passe",
          "emailPlaceholder": "Entrez votre email",
          "passwordPlaceholder": "Entrez votre mot de passe",
          "signIn": "Se Connecter",
          "signingIn": "Connexion en cours...",
          "noAccount": "Pas de compte?",
          "signUp": "S'inscrire"
        },
        "signup": {
          "title": "Créer un Compte",
          "subtitle": "Rejoignez PlantDoc aujourd'hui",
          "name": "Nom Complet",
          "email": "Adresse Email",
          "password": "Mot de Passe",
          "confirmPassword": "Confirmer le Mot de Passe",
          "namePlaceholder": "Entrez votre nom complet",
          "emailPlaceholder": "Entrez votre email",
          "passwordPlaceholder": "Entrez votre mot de passe",
          "confirmPasswordPlaceholder": "Confirmez votre mot de passe",
          "createAccount": "Créer un Compte",
          "creatingAccount": "Création du compte...",
          "haveAccount": "Déjà un compte?",
          "signIn": "Se connecter"
        }
      },
      "dashboard": {
        "sidebar": {
          "upload": "Télécharger Image",
          "history": "Historique",
          "analytics": "Analyses",
          "profile": "Profil",
          "contact": "Nous Contacter",
          "logout": "Déconnexion"
        },
        "upload": {
          "title": "Détection de Maladies des Plantes",
          "subtitle": "Téléchargez une image de votre plante pour détecter les maladies et obtenir des recommandations de traitement",
          "dropZone": "Déposez l'image de votre plante ici",
          "browseText": "ou cliquez pour parcourir depuis votre ordinateur",
          "supportedFormats": "Supporte: JPG, PNG, JPEG (Max 10MB)",
          "chooseFile": "Choisir un Fichier",
          "analyzing": "Analyse de l'Image...",
          "analyzingSubtext": "Notre IA examine votre plante pour détecter les maladies",
          "noAnalysis": "Pas d'Analyse Encore",
          "noAnalysisSubtext": "Téléchargez une image de plante pour voir les résultats de détection"
        },
        "history": {
          "title": "Historique des Téléchargements",
          "subtitle": "Consultez vos résultats d'analyse précédents de maladies des plantes",
          "noHistory": "Pas d'Historique Encore",
          "noHistorySubtext": "Commencez à télécharger des images de plantes pour voir votre historique d'analyse",
          "view": "Voir",
          "severity": "Sévérité"
        },
        "analytics": {
          "title": "Tableau de Bord d'Analyses",
          "subtitle": "Aperçus de votre historique de détection de maladies des plantes",
          "noData": "Aucune Donnée Disponible",
          "noDataSubtext": "Téléchargez et analysez des images de plantes pour voir vos analyses",
          "totalUploads": "Téléchargements Totaux",
          "analyzed": "Analysées",
          "successRate": "Taux de Réussite",
          "avgConfidence": "Confiance Moyenne",
          "diseaseDistribution": "Distribution des Maladies",
          "severityDistribution": "Distribution de Sévérité"
        },
        "profile": {
          "title": "Paramètres du Profil",
          "subtitle": "Gérez les informations de votre compte et vos préférences",
          "personalInfo": "Informations Personnelles",
          "editProfile": "Modifier le Profil",
          "save": "Sauvegarder",
          "cancel": "Annuler",
          "changePhoto": "Changer la Photo",
          "fullName": "Nom Complet",
          "emailAddress": "Adresse Email",
          "signOut": "Se Déconnecter",
          "accountStats": "Statistiques du Compte",
          "memberSince": "Membre Depuis",
          "preferences": "Préférences",
          "emailNotifications": "Notifications Email",
          "analysisAlerts": "Alertes d'Analyse",
          "monthlyReports": "Rapports Mensuels"
        },
        "contact": {
          "title": "Contactez Notre Équipe",
          "subtitle": "Entrez en contact avec notre équipe de développement",
          "teamMembers": "Membres de l'Équipe",
          "contact": "Contact",
          "getInTouch": "Entrer en Contact",
          "getInTouchSubtext": "Des questions ou des commentaires? Nous aimerions vous entendre!"
        }
      },
      "result": {
        "title": "Résultats de l'Analyse",
        "severity": "Sévérité",
        "confidence": "Confiance",
        "recoveryTime": "Temps de récupération attendu",
        "treatment": "Traitement Recommandé",
        "prevention": "Conseils de Prévention",
        "gotIt": "Compris, merci!"
      },
      "chatbot": {
        "title": "Assistant IA",
        "subtitle": "Expert en Agriculture et Soins des Plantes",
        "placeholder": "Demandez sur les soins des plantes...",
        "greeting": "Bonjour! Je suis votre assistant agricole IA. Je peux vous aider avec le diagnostic des maladies des plantes, les recommandations de traitement et les conseils généraux d'agriculture. Comment puis-je vous aider aujourd'hui?"
      },
      "common": {
        "low": "Faible",
        "medium": "Moyen",
        "high": "Élevé",
        "call": "Appeler",
        "sms": "SMS"
      }
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: Object.fromEntries(Object.entries(resources).map(([code, resource]) => [code, { translation: { ...resource.translation, features: featureTranslations[code as keyof typeof featureTranslations] } }])),
    supportedLngs: ['en', 'hi', 'es', 'fr'],
    load: 'languageOnly',
    fallbackLng: 'en',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;