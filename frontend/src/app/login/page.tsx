"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
type Form = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  async function onSubmit(data: Form) {
    setError(null);
    try {
      await login(data.email, data.password);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card w-full max-w-md p-8">
        <h1 className="text-xl font-semibold mb-1">Sign in</h1>
        <p className="text-sm text-gray-500 mb-6">Public Records Research MVP</p>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" {...register("email")} aria-label="email" />
            {errors.email && <p className="text-xs text-red-600 mt-1">Enter a valid email</p>}
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" {...register("password")} aria-label="password" />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn-primary w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="text-sm text-gray-500 mt-4">
          No account?{" "}
          <Link href="/register" className="text-brand-600 hover:underline">
            Create one
          </Link>
        </p>
        <div className="mt-4 text-xs text-gray-400 border-t pt-3 space-y-1">
          <div>
            Demo login (after seeding): <code>demo@example.com / demopassword123</code>
          </div>
          <div>
            After signing in, open <span className="text-gray-500">User Guide</span> in the left
            menu for how to import, search, and review matches.
          </div>
        </div>
      </div>
    </div>
  );
}
