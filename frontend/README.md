
# VideoGenie Front‑End (React 18 · Vite · Tailwind)

Welcome to the official repository for the VideoGenie front-end\! This production-ready single-page application (SPA) provides an intuitive user interface for the VideoGenie back-end services on IBM Cloud. With this application, users can effortlessly transform a text script into a polished, avatar-narrated video.

The process is simple: a user pastes their script, the UI intelligently generates presentation slides, and the user selects an avatar and voice. Once the "Generate" button is clicked, the application provides real-time progress updates via a WebSocket connection. The final MP4 video is then streamed directly from IBM Cloud Object Storage for inline playback.

This guide contains everything you need to get started. Just clone the repository, install the dependencies, and you'll be up and running in minutes.

-----

## ✨ Features

  * **Script-to-Slide Generation:** Automatically converts a multi-line text script into individual presentation slides.
  * **Avatar and Voice Selection:** Users can choose from a dynamic list of available avatars and voices.
  * **Real-Time Progress Tracking:** A live WebSocket connection provides instant feedback on the video generation status.
  * **Direct Video Playback:** The final MP4 video is played directly in the browser from Cloud Object Storage.
  * **Responsive Design:** Built with Tailwind CSS for a seamless experience on any device.
  * **Modern Tech Stack:** Powered by React 18, Vite, and TypeScript for a fast and reliable development experience.

-----

## 🚀 Getting Started

Follow these steps to set up and run the project on your local machine.

### **1. Prerequisites**

  * [Node.js](https://nodejs.org/) (version 18 or higher)
  * [npm](https://www.npmjs.com/) (comes with Node.js)
  * [IBM Cloud CLI](https://cloud.ibm.com/docs/cli) (for production deployment)

### **2. Clone the Repository**

```bash
git clone <repository-url>
cd frontend
```

### **3. Install Dependencies**

Use `npm ci` to ensure a clean and consistent installation based on the `package-lock.json` file.

```bash
npm ci
```

### **4. Configure Environment Variables**

The application requires a connection to the VideoGenie back-end services.

1.  Create a new file named `.env.local` in the `frontend` directory by copying the example file.
    ```bash
    cp .env.example .env.local
    ```
2.  Open `.env.local` and fill in the required values from your IBM Cloud services.
    ```ini
    # .env.local

    # The root URL of your deployed back-end API
    VITE_API_URL=https://api.prd.videogenie.cloud

    # The path for the WebSocket connection (handled by Istio)
    VITE_WS_PATH=/notify

    # App ID OIDC credentials for user authentication
    VITE_APPID_CLIENT_ID=<your-app-id-client-id>
    VITE_APPID_DISCOVERY=<your-app-id-discovery-url>

    # Set to 'true' to enable analytics scripts (optional)
    VITE_ENABLE_ANALYTICS=false
    ```

### **5. Run the Development Server**

Start the local development server, which will be accessible at `http://localhost:5173`.

```bash
npm run dev
```

The application will automatically reload whenever you make changes to the source code.

-----

## 📦 Production Build and Deployment

To deploy the application to a production environment, follow these steps.

1.  **Build the Application:**
    This command compiles the React application into a set of static files in the `dist/` directory.
    ```bash
    npm run build
    ```
2.  **Upload to IBM Cloud Object Storage:**
    Use the IBM Cloud CLI to upload the contents of the `dist/` directory to your designated COS bucket.
    ```bash
    ibmcloud cos upload --bucket vg-spa-assets --key '' --file dist --recursive
    ```
3.  **Purge the CDN Cache (Optional):**
    To ensure users receive the latest version immediately, you can purge the cache in your IBM Cloud Internet Services (CIS) instance.
    ```bash
    ibmcloud cis cache-purge <your-cis-zone-id> --everything
    ```

-----

## 📁 Project Structure

Here is an overview of the key files and directories in the project.

```text
frontend/
├── public/              # Static assets that are not processed by Vite
│   ├── index.html       # The main HTML entry point for the application
│   └── ...
├── src/                 # The main application source code
│   ├── api.ts           # Functions for making API calls to the back-end
│   ├── main.tsx         # The main entry point for the React application
│   ├── App.tsx          # The root component with application routing
│   ├── hooks/           # Custom React hooks (e.g., for WebSockets)
│   ├── components/      # Reusable React components (e.g., SlideEditor)
│   ├── pages/           # Page-level components for different routes
│   └── styles.css       # Global styles and Tailwind CSS directives
├── .env.example         # Example environment variables
├── package.json         # Project dependencies and scripts
├── tailwind.config.js   # Configuration for Tailwind CSS
└── vite.config.ts       # Configuration for the Vite build tool
```