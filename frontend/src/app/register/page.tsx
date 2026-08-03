"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  full_name: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(8, "At least 8 characters"),
  workspace_name: z.string().min(1),
});
type Form = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  async function onSubmit(data: Form) {
    setError(null);
    try {
      await registerUser(data.email, data.password, data.full_name, data.workspace_name);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card w-full max-w-md p-8">
        <h1 className="text-xl font-semibold mb-6">Create your account</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">Full name</label>
            <input className="input" {...register("full_name")} />
            {errors.full_name && <p className="text-xs text-red-600 mt-1">Required</p>}
          </div>
          <div>
            <label className="label">Workspace name</label>
            <input className="input" {...register("workspace_name")} />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" {...register("email")} />
            {errors.email && <p className="text-xs text-red-600 mt-1">Valid email required</p>}
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" {...register("password")} />
            {errors.password && (
              <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>
            )}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn-primary w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating…" : "Create account"}
          </button>
        </form>
        <p className="text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
