import { SignIn } from "@clerk/clerk-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function SignInPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  if (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <SignIn routing="hash" />
      </div>
    );
  }
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center p-6">
      <h1 className="text-2xl font-semibold">Job-hunt</h1>
      <p className="mt-2 text-sm text-slate-500">Test-mode sign-in. Point Clerk keys at this app for production auth.</p>
      <button
        type="button"
        className="mt-6 rounded-md bg-amber-700 px-4 py-2 text-white"
        onClick={async () => {
          try {
            const res = await fetch(`${import.meta.env.VITE_API_BASE || "/api/v1"}/dev/token`, {
              method: "POST",
              headers: { "content-type": "application/json" },
              body: JSON.stringify({ user_id: "user_test_1" }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "token failed");
            localStorage.setItem("jobhunt_test_token", data.token);
            navigate("/");
          } catch (err) {
            setError(err instanceof Error ? err.message : "sign-in failed");
          }
        }}
      >
        Continue as test candidate
      </button>
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
    </main>
  );
}
