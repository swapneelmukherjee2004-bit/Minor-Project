import { Link } from "react-router-dom";
import { EmptyState } from "@/components/ui";

export default function NotFound() {
  return <EmptyState title="Page not found" action={<Link className="text-brand underline" to="/dashboard">Go to the dashboard</Link>}>The page you requested does not exist.</EmptyState>;
}
