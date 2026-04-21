import { useQuery } from "@tanstack/react-query";

import { getDashboardOverview } from "@/features/dashboard/api";

export function useDashboard(ownerUserId?: string) {
  return useQuery({
    queryKey: ["dashboard", "overview", ownerUserId ?? "all"],
    queryFn: () => getDashboardOverview({ ownerUserId }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}
