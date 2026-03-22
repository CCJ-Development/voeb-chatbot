/**
 * ext-i18n: Deutsches Übersetzungs-Dictionary für VÖB Chatbot.
 *
 * Schicht 2 (TranslationProvider) nutzt dieses Dictionary für DOM-basierte
 * Übersetzung. Schicht 1 (t()-Aufrufe in Core-Patches) nutzt es ebenfalls.
 *
 * Regeln:
 * - Keys sind die EXAKTEN englischen Strings wie im Code (Case-sensitiv!)
 * - Formale Sprache (Sie-Form) — Banking-Umfeld
 * - Admin-Bereich wird NICHT übersetzt (nur CCJ/Niko)
 * - Fallback: Fehlender Key → englischer Originaltext
 */
export const DE_TRANSLATIONS: Record<string, string> = {
  // =========================================================================
  // LOGIN / AUTH
  // =========================================================================

  // LoginText.tsx (Core #8) — Schicht 1
  "Welcome to": "Willkommen bei",

  // AuthFlowContainer.tsx (Core #9) — Schicht 1
  "New to": "Neu bei",
  "Create an Account": "Konto erstellen",
  "Already have an account?": "Sie haben bereits ein Konto?",
  "Sign In": "Anmelden",

  // EmailPasswordForm.tsx — Schicht 2
  "Email Address": "E-Mail-Adresse",
  "Email": "E-Mail",
  "Password": "Passwort",
  "email@yourcompany.com": "email@beispiel.de",
  "Join": "Beitreten",
  "Create Account": "Konto erstellen",
  "or continue as guest": "oder als Gast fortfahren",
  "or": "oder",

  // Forgot/Reset Password — Schicht 2
  "Forgot Password": "Passwort vergessen",
  "Reset Password": "Passwort zurücksetzen",
  "Back to Login": "Zurück zur Anmeldung",
  "New Password": "Neues Passwort",
  "Confirm New Password": "Neues Passwort bestätigen",
  "Enter your new password": "Geben Sie Ihr neues Passwort ein",
  "Confirm your new password": "Bestätigen Sie Ihr neues Passwort",

  // Signup — Schicht 2
  "Don't have an account?": "Sie haben noch kein Konto?",
  "Create an account": "Konto erstellen",
  "Complete your sign up": "Registrierung abschließen",
  "Create account": "Konto erstellen",

  // Auth Status Messages — Schicht 2
  "Joining...": "Beitritt...",
  "Creating account...": "Konto wird erstellt...",
  "Signing in...": "Anmeldung...",
  "Account created. Signing in...": "Konto erstellt. Anmeldung...",
  "Signed in successfully.": "Erfolgreich angemeldet.",

  // Auth Error Messages — Schicht 2
  "Invalid email or password": "Ungültige E-Mail-Adresse oder Passwort",
  "Too many requests. Please try again later.":
    "Zu viele Anfragen. Bitte versuchen Sie es später erneut.",
  "An account already exists with the specified email.":
    "Es existiert bereits ein Konto mit dieser E-Mail-Adresse.",
  "Unknown error": "Unbekannter Fehler",
  "Create an account to set a password":
    "Erstellen Sie ein Konto, um ein Passwort festzulegen",
  "Password is required": "Passwort ist erforderlich",
  "Passwords must match": "Passwörter müssen übereinstimmen",
  "Confirm Password is required": "Passwortbestätigung ist erforderlich",
  "Invalid or missing reset token.":
    "Ungültiger oder fehlender Token zum Zurücksetzen.",
  "An error occurred. Please try again.":
    "Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
  "An error occurred during password reset.":
    "Beim Zurücksetzen des Passworts ist ein Fehler aufgetreten.",
  "An unexpected error occurred. Please try again.":
    "Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es erneut.",
  "Your email has been verified! Please sign in to continue.":
    "Ihre E-Mail-Adresse wurde bestätigt! Bitte melden Sie sich an.",
  "Password reset email sent. Please check your inbox.":
    "E-Mail zum Zurücksetzen des Passworts wurde gesendet. Bitte prüfen Sie Ihren Posteingang.",
  "Password reset successfully. Redirecting to login...":
    "Passwort erfolgreich zurückgesetzt. Weiterleitung zur Anmeldung...",
  "Account created successfully. Please log in.":
    "Konto erfolgreich erstellt. Bitte melden Sie sich an.",

  // Signup-Seite: "Get started with Onyx" soll komplett raus (Niko-Entscheidung)
  "Get started with Onyx": "",

  // Passwort-Validierung (dynamisch mit Variable, häufigster Fall: 8 Zeichen)
  "Password must be at least 8 characters":
    "Passwort muss mindestens 8 Zeichen lang sein",

  // Onboarding — Namensabfrage
  "What should Onyx call you?": "Wie sollen wir Sie nennen?",
  "We will display this name in the app.":
    "Dieser Name wird in der Anwendung angezeigt.",

  // =========================================================================
  // CHAT UI
  // =========================================================================

  // AppInputBar.tsx Placeholders — Schicht 2
  "How can I help you today?": "Wie kann ich Ihnen helfen?",
  "Listening...": "Ich höre zu...",
  "Onyx is speaking...": "Sprachausgabe...",
  "Search connected sources": "Verbundene Quellen durchsuchen",

  // greetingMessages.ts (überschrieben via ext-branding custom_greeting_message)
  "How can I help?": "Wie kann ich Ihnen helfen?",
  "Let's get started.": "Lassen Sie uns beginnen.",

  // AppInputBar.tsx Actions — Schicht 2
  "Attach Files": "Dateien anhängen",
  "Deep Research": "Tiefenrecherche",
  "Read this tab": "Tab einlesen",
  "Reading tab...": "Tab wird eingelesen...",

  // Message Actions — Schicht 2
  "Regenerate": "Neu generieren",
  "There was an error with the response.":
    "Bei der Antwort ist ein Fehler aufgetreten.",
  "Stack trace": "Fehlerdetails",
  "Sources": "Quellen",
  "Cited Sources": "Zitierte Quellen",
  "Found Sources": "Gefundene Quellen",
  "Good Response": "Gute Antwort",
  "Bad Response": "Schlechte Antwort",
  "Remove Like": "Bewertung entfernen",
  "Remove Dislike": "Bewertung entfernen",

  // Copy — Schicht 2
  "Copy": "Kopieren",
  "Copied!": "Kopiert!",
  "Failed to copy": "Kopieren fehlgeschlagen",
  "Copy Link": "Link kopieren",
  "Copy link": "Link kopieren",

  // Voice/TTS — Schicht 2
  "Stop playback": "Wiedergabe stoppen",
  "Read aloud": "Vorlesen",

  // Image Generation — Schicht 2
  "Generating image...": "Bild wird generiert...",
  "Generating images...": "Bilder werden generiert...",

  // =========================================================================
  // SIDEBAR NAVIGATION (AppSidebar.tsx)
  // =========================================================================

  "Search Chats": "Chats durchsuchen",
  "Explore Agents": "Agenten entdecken",
  "More Agents": "Weitere Agenten",
  "Admin Panel": "Adminbereich",
  "Curator Panel": "Kuratorbereich",
  "Recents": "Verlauf",
  "Try sending a message! Your chat history will appear here.":
    "Senden Sie eine Nachricht! Ihr Chatverlauf erscheint hier.",

  // ChatButton.tsx Context Menu
  "Share": "Teilen",
  "Rename": "Umbenennen",
  "Delete": "Löschen",
  "Move to Project": "In Projekt verschieben",
  "Search Projects": "Projekte suchen",
  "Delete Chat": "Chat löschen",
  "Are you sure you want to delete this chat? This action cannot be undone.":
    "Möchten Sie diesen Chat wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",

  // ProjectFolderButton.tsx
  "Rename Project": "Projekt umbenennen",
  "Delete Project": "Projekt löschen",
  "Are you sure you want to delete this project? This action cannot be undone.":
    "Möchten Sie dieses Projekt wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.",

  // AgentButton.tsx
  "Unpin Agent": "Agent lösen",

  // ChatSearchCommandMenu.tsx
  "Search chat sessions, projects...": "Chats und Projekte suchen...",
  "New Session": "Neue Sitzung",
  "Recent Sessions": "Letzte Sitzungen",
  "Recent": "Zuletzt",
  "Projects": "Projekte",
  "New Project": "Neues Projekt",
  "No results found": "Keine Ergebnisse gefunden",
  "No chats or projects yet": "Noch keine Chats oder Projekte",
  "No more results": "Keine weiteren Ergebnisse",

  // =========================================================================
  // USER MENU (UserAvatarPopover.tsx)
  // =========================================================================

  "User Settings": "Benutzereinstellungen",
  "Notifications": "Benachrichtigungen",
  "Help & FAQ": "Hilfe & FAQ",
  "Log in": "Anmelden",
  "Log out": "Abmelden",

  // =========================================================================
  // AGENTS PAGE (AgentsNavigationPage.tsx)
  // =========================================================================

  "Agents": "Agenten",
  "Customize AI behavior and knowledge for you and your team's use cases.":
    "KI-Verhalten und Wissen für Ihr Team anpassen.",
  "Search agents...": "Agenten suchen...",
  "All Agents": "Alle Agenten",
  "Your Agents": "Ihre Agenten",
  "Everyone": "Alle",
  "All Actions": "Alle Aktionen",
  "No Agents found": "Keine Agenten gefunden",
  "New Agent": "Neuer Agent",
  "Filter actions...": "Aktionen filtern...",
  "Created by...": "Erstellt von...",
  "No Knowledge": "Kein Wissen",
  "No Actions": "Keine Aktionen",

  // =========================================================================
  // AGENT ERSTELLEN / BEARBEITEN (AgentEditorPage.tsx)
  // =========================================================================

  "Create Agent": "Agent erstellen",
  "Edit Agent": "Agent bearbeiten",
  "Create": "Erstellen",
  "Name": "Name",
  "Name your agent": "Benennen Sie Ihren Agenten",
  "Description": "Beschreibung",
  "(Optional)": "(Optional)",
  "What does this agent do?": "Was macht dieser Agent?",
  "Agent Avatar": "Agent-Avatar",
  "Instructions": "Anweisungen",
  "Add instructions to tailor the response for this agent.":
    "Fügen Sie Anweisungen hinzu, um die Antworten dieses Agenten anzupassen.",
  "Conversation Starters": "Gesprächseinstiege",
  "Example messages that help users understand what this agent can do and how to interact with it effectively.":
    "Beispielnachrichten, die Nutzern zeigen, was dieser Agent kann und wie man ihn effektiv nutzt.",
  "Knowledge": "Wissen",
  "Add specific connectors and documents for this agent to use to inform its responses.":
    "Fügen Sie Anbindungen und Dokumente hinzu, die der Agent für seine Antworten nutzen soll.",
  "Use Knowledge": "Wissen verwenden",
  "Let this agent reference these documents to inform its responses.":
    "Diesem Agenten erlauben, diese Dokumente für seine Antworten zu nutzen.",
  "Add documents or connected sources to use for this agent.":
    "Dokumente oder Anbindungen für diesen Agenten hinzufügen.",

  // Agent-Tools
  "Search the web for real-time information and up-to-date results.":
    "Das Web nach aktuellen Informationen und Ergebnissen durchsuchen.",
  "Open URL": "URL öffnen",
  "Fetch and read content from web URLs.":
    "Inhalte von Web-URLs abrufen und lesen.",
  "Generate and run code.": "Code generieren und ausführen.",

  // Agent — Advanced Options
  "Advanced Options": "Erweiterte Optionen",
  "Fine-tune agent prompts and knowledge.":
    "Agent-Prompts und Wissen feinabstimmen.",
  "Share This Agent": "Diesen Agenten teilen",
  "with other users, groups, or everyone in your organization.":
    "mit anderen Nutzern, Gruppen oder allen in Ihrer Organisation.",
  "Feature This Agent": "Diesen Agenten hervorheben",
  "Show this agent at the top of the explore agents list and automatically pin it to the sidebar for new users with access.":
    "Diesen Agenten oben in der Agentenliste anzeigen und automatisch für neue Nutzer in der Seitenleiste anheften.",
  "Knowledge Cutoff Date": "Wissensstichtag",
  "Set the knowledge cutoff date for this agent. The agent will only use information up to this date.":
    "Wissensstichtag für diesen Agenten festlegen. Der Agent verwendet nur Informationen bis zu diesem Datum.",
  "Select Date": "Datum wählen",
  "Overwrite System Prompt": "System-Prompt überschreiben",
  "Completely replace the base system prompt. This might affect response quality since it will also overwrite useful system instructions (e.g. \"You (the LLM) can provide markdown and it will be rendered\").":
    "Den Basis-System-Prompt vollständig ersetzen. Dies kann die Antwortqualität beeinträchtigen, da auch nützliche Systemanweisungen überschrieben werden.",
  "Reminders": "Erinnerungen",
  "Append a brief reminder to the prompt messages. Use this to remind the agent if you find that it tends to forget certain instructions as the chat progresses. This should be brief and not interfere with the user messages.":
    "Eine kurze Erinnerung an die Prompt-Nachrichten anhängen. Nutzen Sie dies, wenn der Agent im Gesprächsverlauf bestimmte Anweisungen vergisst. Die Erinnerung sollte kurz sein.",
  "User Default": "Benutzer-Standard",
  "System Default": "System-Standard",

  // Starter Messages (constants.ts)
  "Give me an overview of some documents.":
    "Geben Sie mir einen Überblick über einige Dokumente.",
  "Find the latest sales report.":
    "Finden Sie den neuesten Verkaufsbericht.",
  "Compile a list of our engineering goals for this quarter.":
    "Erstellen Sie eine Liste unserer technischen Ziele für dieses Quartal.",
  "Summarize my goals for today.":
    "Fassen Sie meine heutigen Ziele zusammen.",

  // =========================================================================
  // PROJECTS (CreateProjectModal.tsx)
  // =========================================================================

  "Create New Project": "Neues Projekt erstellen",
  "Use projects to organize your files and chats in one place, and add custom instructions for ongoing work.":
    "Nutzen Sie Projekte, um Dateien und Chats an einem Ort zu organisieren und individuelle Anweisungen hinzuzufügen.",
  "Project Name": "Projektname",
  "What are you working on?": "Woran arbeiten Sie?",
  "Create Project": "Projekt erstellen",

  // =========================================================================
  // PROJEKT-DETAIL (ProjectContextPanel.tsx)
  // =========================================================================

  "Add instructions to tailor the response in this project.":
    "Fügen Sie Anweisungen hinzu, um die Antworten in diesem Projekt anzupassen.",
  "Set Instructions": "Anweisungen festlegen",
  "Files": "Dateien",
  "Chats in this project can access these files.":
    "Chats in diesem Projekt können auf diese Dateien zugreifen.",
  "Add Files": "Dateien hinzufügen",
  "Add documents, texts, or images to use in the project. Drag & drop supported.":
    "Dokumente, Texte oder Bilder zum Projekt hinzufügen. Drag & Drop wird unterstützt.",
  "Recent Chats": "Letzte Chats",
  "No chats yet.": "Noch keine Chats.",

  // Projekt-Anweisungen-Modal
  "Set Project Instructions": "Projektanweisungen festlegen",
  "Specify the behaviors or tone for the chat sessions in this project.":
    "Legen Sie das Verhalten oder den Ton für die Chats in diesem Projekt fest.",
  "My goal with is to... be sure to... in your responses.":
    "Mein Ziel ist es... achten Sie darauf... in Ihren Antworten.",
  "Save Instructions": "Anweisungen speichern",

  // =========================================================================
  // SHARE AGENT MODAL
  // =========================================================================

  "Share Agent": "Agent teilen",
  "Users & Groups": "Benutzer & Gruppen",
  "Your Organization": "Ihre Organisation",
  "Add users and groups": "Benutzer und Gruppen hinzufügen",
  "You": "Sie",
  "Owner": "Eigentümer",
  "This agent is public to your organization.":
    "Dieser Agent ist für Ihre Organisation öffentlich.",
  "Everyone in your organization has access to this agent.":
    "Alle in Ihrer Organisation haben Zugriff auf diesen Agenten.",

  // =========================================================================
  // UPLOAD FILES (FilePickerPopover.tsx)
  // =========================================================================

  "Upload Files": "Dateien hochladen",
  "Upload a file from your device": "Datei von Ihrem Gerät hochladen",
  "Recent Files": "Letzte Dateien",
  "All Recent Files": "Alle letzten Dateien",
  "No files uploaded yet": "Noch keine Dateien hochgeladen",
  "No files yet": "Noch keine Dateien",
  "No files found": "Keine Dateien gefunden",
  "Drop files here to add to this project":
    "Dateien hierher ziehen, um sie zum Projekt hinzuzufügen",
  "Processing...": "Wird verarbeitet...",

  // =========================================================================
  // ACTIONS MENU (ActionsPopover)
  // =========================================================================

  "Search Actions": "Aktionen suchen",
  "Internal Search": "Interne Suche",
  "Image Generation": "Bilderzeugung",
  "Web Search": "Websuche",
  "Code Interpreter": "Code-Interpreter",
  "More Actions": "Weitere Aktionen",

  // =========================================================================
  // MODEL SELECTOR (LLMPopover.tsx)
  // =========================================================================

  "Search models...": "Modelle suchen...",
  "Reasoning": "Reasoning",
  "Vision": "Vision",
  "No models found": "Keine Modelle gefunden",

  // =========================================================================
  // SETTINGS PAGE (User Settings)
  // =========================================================================

  // Seiten-Titel + Navigation
  "Settings": "Einstellungen",
  "General": "Allgemein",
  "Chat Preferences": "Chat-Einstellungen",
  "Accounts & Access": "Konten & Zugriff",

  "Profile": "Profil",
  "Full Name": "Vollständiger Name",
  "We'll display this name in the app.": "Dieser Name wird in der App angezeigt.",
  "Your name": "Ihr Name",
  "Work Role": "Berufsrolle",
  "Share your role to better tailor responses.":
    "Teilen Sie Ihre Rolle mit, um bessere Antworten zu erhalten.",
  "Your role": "Ihre Rolle",
  "Appearance": "Darstellung",
  "Color Mode": "Farbmodus",
  "Select your preferred color mode for the UI.":
    "Wählen Sie Ihren bevorzugten Farbmodus.",
  "Auto": "Automatisch",
  "Light": "Hell",
  "Dark": "Dunkel",
  "Chat Background": "Chat-Hintergrund",
  "None": "Keiner",
  "Danger Zone": "Gefahrenbereich",
  "Delete All Chats": "Alle Chats löschen",
  "Permanently delete all your chat sessions.":
    "Alle Ihre Chat-Sitzungen unwiderruflich löschen.",
  "All your chat sessions and history will be permanently deleted. Deletion cannot be undone.":
    "Alle Ihre Chat-Sitzungen und der Verlauf werden unwiderruflich gelöscht. Diese Aktion kann nicht rückgängig gemacht werden.",
  "Are you sure you want to delete all chats?":
    "Möchten Sie wirklich alle Chats löschen?",
  "All your chat sessions have been deleted.":
    "Alle Ihre Chat-Sitzungen wurden gelöscht.",
  "Failed to delete all chat sessions":
    "Chat-Sitzungen konnten nicht gelöscht werden",
  "Chats": "Chats",
  "Default Model": "Standardmodell",
  "This model will be used by Onyx by default in your chats.":
    "Dieses Modell wird standardmäßig in Ihren Chats verwendet.",
  "Chat Auto-scroll": "Chat-Auto-Scroll",
  "Automatically scroll to new content as chat generates response.":
    "Automatisch zu neuen Inhalten scrollen, während die Antwort generiert wird.",
  "Default App Mode": "Standard-App-Modus",
  "Choose whether new sessions start in Search or Chat mode.":
    "Wählen Sie, ob neue Sitzungen im Such- oder Chatmodus starten.",
  "Chat": "Chat",
  "Search": "Suche",
  "Personal Preferences": "Persönliche Einstellungen",
  "Provide your custom preferences in natural language.":
    "Geben Sie Ihre Einstellungen in natürlicher Sprache an.",
  "Describe how you want the system to behave and the tone it should use.":
    "Beschreiben Sie, wie sich das System verhalten und welchen Ton es verwenden soll.",
  "Memory": "Gedächtnis",
  "Reference Stored Memories": "Gespeicherte Erinnerungen verwenden",
  "Let Onyx reference stored memories in chats.":
    "Gespeicherte Erinnerungen in Chats verwenden.",
  "Update Memories": "Erinnerungen aktualisieren",
  "Let Onyx generate and update stored memories.":
    "Erinnerungen automatisch generieren und aktualisieren.",
  "Prompt Shortcuts": "Prompt-Kurzbefehle",
  "Use Prompt Shortcuts": "Prompt-Kurzbefehle verwenden",
  "Enable shortcuts to quickly insert common prompts.":
    "Kurzbefehle zum schnellen Einfügen häufiger Prompts aktivieren.",
  "Preferences saved": "Einstellungen gespeichert",
  "Failed to save preferences": "Einstellungen konnten nicht gespeichert werden",
  "Personalization updated successfully": "Personalisierung erfolgreich aktualisiert",
  "Failed to update personalization": "Personalisierung konnte nicht aktualisiert werden",
  "Voice": "Sprache",
  "Auto-Send": "Automatisch senden",
  "Automatically send voice input when recording stops.":
    "Spracheingabe automatisch senden, wenn die Aufnahme endet.",
  "Auto-Playback": "Automatische Wiedergabe",
  "Automatically play voice responses.":
    "Sprachantworten automatisch abspielen.",
  "Playback Speed": "Wiedergabegeschwindigkeit",
  "Adjust the speed of voice playback.":
    "Geschwindigkeit der Sprachwiedergabe anpassen.",
  "Accounts": "Konten",
  "Your account email address.": "Ihre Konto-E-Mail-Adresse.",
  "Update your account password.": "Ihr Kontopasswort aktualisieren.",
  "Change Password": "Passwort ändern",
  "Current Password": "Aktuelles Passwort",
  "Password updated successfully": "Passwort erfolgreich aktualisiert",
  "Updating...": "Wird aktualisiert...",
  "Update": "Aktualisieren",
  "Access Tokens": "Zugriffstoken",
  "New Access Token": "Neuer Zugriffstoken",
  "Loading tokens...": "Token werden geladen...",
  "No access tokens created.": "Keine Zugriffstoken erstellt.",
  "Connectors": "Anbindungen",
  "Connected": "Verbunden",
  "Paused": "Pausiert",
  "Not connected": "Nicht verbunden",
  "Connect": "Verbinden",
  "Disconnect": "Trennen",
  "Disconnecting...": "Wird getrennt...",
  "Disconnected successfully": "Erfolgreich getrennt",
  "Failed to disconnect": "Trennung fehlgeschlagen",
  "No connectors set up for your organization.":
    "Keine Anbindungen für Ihre Organisation eingerichtet.",

  // =========================================================================
  // DATE / TIME LABELS
  // =========================================================================

  "Today": "Heute",
  "Yesterday": "Gestern",

  // =========================================================================
  // FEEDBACK MODAL
  // =========================================================================

  "Feedback": "Feedback",
  "Provide Additional Details": "Weitere Details angeben",
  "Submitting...": "Wird gesendet...",
  "Feedback is required": "Feedback ist erforderlich",

  // =========================================================================
  // SHARE MODAL
  // =========================================================================

  "Share link copied to clipboard!":
    "Freigabelink in die Zwischenablage kopiert!",
  "Chat is now private": "Chat ist jetzt privat",
  "Failed to generate share link":
    "Freigabelink konnte nicht erstellt werden",
  "Failed to make chat private":
    "Chat konnte nicht auf privat gesetzt werden",

  // =========================================================================
  // COMMON BUTTONS
  // =========================================================================

  "Submit": "Absenden",
  "Cancel": "Abbrechen",
  "Save": "Speichern",
  "Close": "Schließen",
  "Back": "Zurück",
  "Next": "Weiter",
  "Continue": "Fortfahren",
  "Confirm": "Bestätigen",
  "Done": "Fertig",
  "Apply": "Anwenden",
  "Edit": "Bearbeiten",
  "More": "Mehr",

  // =========================================================================
  // LOADING / EMPTY STATES
  // =========================================================================

  "Loading...": "Wird geladen...",
  "No data available": "Keine Daten verfügbar",

  // =========================================================================
  // ERROR MESSAGES (Toasts)
  // =========================================================================

  "An error occurred": "Ein Fehler ist aufgetreten",
  "An error occurred.": "Ein Fehler ist aufgetreten.",
  "Please try again.": "Bitte versuchen Sie es erneut.",
  "Failed to delete chat. Please try again.":
    "Chat konnte nicht gelöscht werden. Bitte versuchen Sie es erneut.",
  "Failed to logout": "Abmeldung fehlgeschlagen",
  "Could not play audio": "Audio konnte nicht abgespielt werden",
  "Could not access microphone": "Zugriff auf Mikrofon nicht möglich",
  "Could not auto-start microphone":
    "Mikrofon konnte nicht automatisch gestartet werden",
};
