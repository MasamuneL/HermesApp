import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut
} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const firebaseConfig = {
  apiKey:            "AIzaSyDlcgsY3l6aOcv9k7AXg-aDJEboxchd84M",
  authDomain:        "hermes-9d328.firebaseapp.com",
  projectId:         "hermes-9d328",
  storageBucket:     "hermes-9d328.firebasestorage.app",
  messagingSenderId: "979608440750",
  appId:             "1:979608440750:web:c0f9b587ae169e0da7023f"
};

const app      = initializeApp(firebaseConfig);
const auth     = getAuth(app);
const provider = new GoogleAuthProvider();

export const API_BASE = "http://localhost:8000";

// Obtiene el token Firebase del usuario actual
export async function getToken() {
  const user = auth.currentUser;
  if (!user) return null;
  return await user.getIdToken();
}

// Headers base para todas las peticiones al back
export async function authHeaders(extra = {}) {
  const token = await getToken();
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`,
    ...extra
  };
}

// Redirige al login si no hay sesión activa
export function requireAuth(callback) {
  onAuthStateChanged(auth, user => {
    if (!user) {
      window.location.href = "login.html";
    } else {
      callback(user);
    }
  });
}

export { auth, provider, onAuthStateChanged, signInWithEmailAndPassword,
         createUserWithEmailAndPassword, signInWithPopup, signOut };
