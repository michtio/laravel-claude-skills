<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Composer\InstalledVersions;

/**
 * Boost's core guideline source (`.ai/boost/core.blade.php` in laravel/boost) as
 * installed in the project, with the Boost version it came from.
 *
 * The project's own vendor/ comes first; the Boost installed with the running
 * application is the fallback (the same install when the setup runs through the
 * project's own artisan or Testbench).
 *
 * @author michtio
 */
final class BoostCore
{
    // Constants
    // =========================================================================

    /**
     * Path of the core guideline inside the laravel/boost package.
     */
    public const SOURCE = '.ai/boost/core.blade.php';

    // Public Methods
    // =========================================================================

    /**
     * Describe a located core guideline.
     *
     * @author michtio
     */
    public function __construct(
        public readonly string $content,
        public readonly string $version,
    ) {
    }

    /**
     * Locate Boost's core guideline for the project at the given root.
     *
     * @throws SetupException When laravel/boost is not installed.
     * @author michtio
     */
    public static function locate(string $root): self
    {
        $vendored = $root.'/vendor/laravel/boost/'.self::SOURCE;

        if (is_file($vendored)) {
            return new self((string) file_get_contents($vendored), self::vendoredVersion($root) ?? 'unknown');
        }

        if (class_exists(InstalledVersions::class) && InstalledVersions::isInstalled('laravel/boost')) {
            $path = InstalledVersions::getInstallPath('laravel/boost');

            if ($path !== null && is_file($path.'/'.self::SOURCE)) {
                return new self(
                    (string) file_get_contents($path.'/'.self::SOURCE),
                    InstalledVersions::getPrettyVersion('laravel/boost') ?? 'unknown',
                );
            }
        }

        throw new SetupException('laravel/boost is not installed in this project. Install Boost first (composer require --dev laravel/boost), then run the setup again; nothing was written.');
    }

    // Private Methods
    // =========================================================================

    /**
     * The laravel/boost version recorded in the project's vendor/composer/installed.json.
     *
     * @author michtio
     */
    private static function vendoredVersion(string $root): ?string
    {
        $file = $root.'/vendor/composer/installed.json';

        if (! is_file($file)) {
            return null;
        }

        $installed = json_decode((string) file_get_contents($file), true);
        $packages = is_array($installed) ? ($installed['packages'] ?? $installed) : [];

        foreach (is_array($packages) ? $packages : [] as $package) {
            if (is_array($package) && ($package['name'] ?? null) === 'laravel/boost' && is_string($package['version'] ?? null)) {
                return $package['version'];
            }
        }

        return null;
    }
}
