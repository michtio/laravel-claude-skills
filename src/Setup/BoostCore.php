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
 * project's own artisan or Testbench). The version comes from
 * vendor/composer/installed.json, then composer.lock, then Composer's runtime data.
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
        public readonly ?string $version,
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
            return new self(
                (string) file_get_contents($vendored),
                self::vendoredVersion($root) ?? self::lockedVersion($root) ?? self::runningVersion(),
            );
        }

        if (class_exists(InstalledVersions::class) && InstalledVersions::isInstalled('laravel/boost')) {
            $path = InstalledVersions::getInstallPath('laravel/boost');

            if ($path !== null && is_file($path.'/'.self::SOURCE)) {
                return new self(
                    (string) file_get_contents($path.'/'.self::SOURCE),
                    self::runningVersion() ?? self::lockedVersion($root),
                );
            }
        }

        throw new SetupException('laravel/boost is not installed in this project. Install Boost first (composer require --dev laravel/boost), then run the setup again; nothing was written.');
    }

    /**
     * The version for a header: "laravel/boost <version>", or a plain statement when no record names it.
     *
     * @author michtio
     */
    public function label(): string
    {
        return $this->version === null ? 'laravel/boost (version not recorded)' : 'laravel/boost '.$this->version;
    }

    // Private Methods
    // =========================================================================

    /**
     * The laravel/boost version in the project's composer.lock (packages or packages-dev).
     *
     * @author michtio
     */
    private static function lockedVersion(string $root): ?string
    {
        $file = $root.'/composer.lock';

        if (! is_file($file)) {
            return null;
        }

        $lock = json_decode((string) file_get_contents($file), true);

        if (! is_array($lock)) {
            return null;
        }

        return self::findVersion(array_merge(
            is_array($lock['packages'] ?? null) ? $lock['packages'] : [],
            is_array($lock['packages-dev'] ?? null) ? $lock['packages-dev'] : [],
        ));
    }

    /**
     * The laravel/boost version installed with the running application, if Composer knows it.
     *
     * @author michtio
     */
    private static function runningVersion(): ?string
    {
        if (! class_exists(InstalledVersions::class) || ! InstalledVersions::isInstalled('laravel/boost')) {
            return null;
        }

        return InstalledVersions::getPrettyVersion('laravel/boost');
    }

    /**
     * The version of laravel/boost in a list of Composer package records.
     *
     * @param array<mixed> $packages
     * @author michtio
     */
    private static function findVersion(array $packages): ?string
    {
        foreach ($packages as $package) {
            if (is_array($package) && ($package['name'] ?? null) === 'laravel/boost' && is_string($package['version'] ?? null)) {
                return $package['version'];
            }
        }

        return null;
    }

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

        return self::findVersion(is_array($packages) ? $packages : []);
    }
}
