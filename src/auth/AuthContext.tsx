
import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode
} from "react";

interface User {
  id: string;
  email: string;
  fullName: string;
  roles: string[];
  permissions: string[];
  access_token: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SESSION_KEY = "octomation_session";
const API_URL = "http://127.0.0.1:4002/iam";

function encryptSession(data: unknown): string {
  const serialized = JSON.stringify(data);

  if (window.api?.auth?.encrypt) {
    try {
      return window.api.auth.encrypt(serialized);
    } catch {
      // Usa el fallback de serialización.
    }
  }

  return btoa(unescape(encodeURIComponent(serialized)));
}

function decryptSession(encrypted: string): any {
  if (window.api?.auth?.decrypt) {
    try {
      return JSON.parse(window.api.auth.decrypt(encrypted));
    } catch {
      // Intenta recuperar la sesión con el formato de fallback.
    }
  }

  try {
    return JSON.parse(
      decodeURIComponent(escape(atob(encrypted)))
    );
  } catch {
    return null;
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");

  if (parts.length !== 3) {
    throw new Error("El servidor devolvió un JWT inválido");
  }

  const base64 = parts[1]
    .replace(/-/g, "+")
    .replace(/_/g, "/");

  const padded = base64.padEnd(
    base64.length + ((4 - base64.length % 4) % 4),
    "="
  );

  const bytes = Uint8Array.from(
    atob(padded),
    (char) => char.charCodeAt(0)
  );

  const payload = new TextDecoder().decode(bytes);

  return JSON.parse(payload);
}

export function AuthProvider({
  children
}: {
  children: ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(SESSION_KEY);

      if (stored) {
        const session = decryptSession(stored);
        const accessToken = session?.user?.access_token;

        if (typeof accessToken === "string") {
          const payload = decodeJwtPayload(accessToken);

          if (
            typeof payload.exp === "number" &&
            payload.exp * 1000 <= Date.now()
          ) {
            localStorage.removeItem(SESSION_KEY);
          } else {
            setUser(session.user);
          }
        } else {
          localStorage.removeItem(SESSION_KEY);
        }
      }
    } catch {
      localStorage.removeItem(SESSION_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        email,
        password
      })
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(
        data?.message || "No se pudo iniciar sesión"
      );
    }

    const accessToken = data?.access_token;

    if (typeof accessToken !== "string") {
      throw new Error(
        "La respuesta del servidor no contiene access_token"
      );
    }

    const payload = decodeJwtPayload(accessToken);
    const responseUser = data?.user ?? {};

    // El backend puede devolver el identificador como `sub` (estándar JWT)
    // o como `id` (payload actual), por lo que se aceptan ambos.
    const userId = payload.sub ?? payload.id ?? responseUser.id;
    const userEmail = payload.email ?? responseUser.email;
    const userFullName =
      payload.fullName ?? payload.full_name ?? responseUser.fullName;

    const rawRoles = payload.roles ?? payload.role ?? responseUser.role;
    const roles = Array.isArray(rawRoles)
      ? rawRoles
      : typeof rawRoles === "string"
        ? [rawRoles]
        : [];

    const rawPermissions =
      payload.permissions ?? responseUser.permissions;
    const permissions = Array.isArray(rawPermissions)
      ? rawPermissions
      : [];

    if (typeof userId !== "string" && typeof userId !== "number") {
      throw new Error("El JWT no contiene un identificador válido");
    }

    if (
      typeof userEmail !== "string" ||
      typeof userFullName !== "string"
    ) {
      throw new Error("El payload del JWT tiene un formato inválido");
    }

    const sessionUser: User = {
      id: String(userId),
      email: userEmail,
      fullName: userFullName,
      roles,
      permissions,
      access_token: accessToken
    };

    localStorage.setItem(
      SESSION_KEY,
      encryptSession({ user: sessionUser })
    );

    setUser(sessionUser);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(SESSION_KEY);
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error(
      "useAuth debe usarse dentro de AuthProvider"
    );
  }

  return context;
}
