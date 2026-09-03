import type { NextConfig } from "next";

const isGitHubPages = process.env.GITHUB_PAGES === "true";
const repositoryName = process.env.GITHUB_REPOSITORY?.split("/")[1] ?? "my-coffeediy.github.io";
const isAccountPage = repositoryName.endsWith(".github.io");
const basePath = isGitHubPages && !isAccountPage ? `/${repositoryName}` : "";

const nextConfig: NextConfig = {
  ...(isGitHubPages
    ? {
        output: "export" as const,
        trailingSlash: true,
        basePath,
        assetPrefix: basePath,
        images: { unoptimized: true },
        typescript: { tsconfigPath: "tsconfig.github.json" },
      }
    : {}),
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
