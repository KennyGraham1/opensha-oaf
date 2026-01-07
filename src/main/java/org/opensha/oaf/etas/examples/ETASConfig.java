package org.opensha.oaf.etas.examples;

import java.io.FileReader;
import java.io.IOException;
import com.google.gson.Gson;

/**
 * Configuration POJO for ETAS model runs.
 * Load from JSON using ETASConfig.loadFromFile(path).
 */
public class ETASConfig {

    public String eventId;
    public String dataSource;

    public WindowConfig dataWindow;
    public WindowConfig forecastWindow;

    public RegionConfig region;
    public CatalogConfig catalog;
    public PriorsConfig priors;
    public GridSearchConfig gridSearch;
    public SimulationConfig simulation;
    public OutputConfig output;

    // --- Nested Config Classes ---

    public static class WindowConfig {
        public double minDays;
        public double maxDays;
    }

    public static class RegionConfig {
        public double radiusKm;
        public double minDepth;
        public double maxDepth;
    }

    public static class CatalogConfig {
        public double magComplete;
    }

    public static class PriorsConfig {
        public double aMean;
        public double aSigma;
        public double pMean;
        public double pSigma;
        public double cMean;
        public double logcSigma;
        public double alpha;
        public double b;
        public double refMag;
    }

    public static class GridSearchConfig {
        public double amsMin, amsMax;
        public int amsN;
        public double aMin, aMax;
        public int aN;
        public double pMin, pMax;
        public int pN;
        public double cMin, cMax;
        public int cN;
    }

    public static class SimulationConfig {
        public int nSims;
        public int maxGenerations;
        public double maxMag;
        public boolean timeDependentMc;
        public boolean fitMSProductivity;
    }

    public static class OutputConfig {
        public String summaryFile;
        public String catalogDir;
    }

    // --- Static Loader ---

    public static ETASConfig loadFromFile(String path) throws IOException {
        Gson gson = new Gson();
        try (FileReader reader = new FileReader(path)) {
            return gson.fromJson(reader, ETASConfig.class);
        }
    }
}
