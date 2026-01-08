package org.opensha.oaf.etas.examples;

import java.io.IOException;
import java.text.DecimalFormat;
import org.opensha.commons.geo.Location;
import org.opensha.oaf.etas.ETAS_AftershockModel_Generic;
import org.opensha.oaf.etas.ETAS_AftershockModel_SequenceSpecific;
import org.opensha.oaf.etas.ETAS_StatsCalc;
import org.opensha.oaf.etas.GenericETAS_Parameters;
import org.opensha.oaf.util.SphLatLon;
import org.opensha.oaf.util.SphRegion;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupList;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupture;
import org.opensha.oaf.etas.ETAS_GeoNetAccessor;

/**
 * Config-driven ETAS Demo for New Zealand (GeoNet data).
 * 
 * Usage:
 * ./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ
 * --args="--config etas_config.json"
 * 
 * Or with legacy CLI args:
 * ./gradlew run -DmainClass=org.opensha.oaf.etas.examples.ETAS_Demo_NZ
 * --args="2016p858000 7 14"
 */
public class ETAS_Demo_NZ {

    public static void main(String[] args) {
        System.out.println("ETAS Demo (NZ): Config-Driven Runner");

        ETASConfig config = null;

        // --- Argument Parsing ---
        // Check for --config flag
        if (args.length >= 2 && args[0].equals("--config")) {
            String configPath = args[1];
            System.out.println("Loading config from: " + configPath);
            try {
                config = ETASConfig.loadFromFile(configPath);
            } catch (IOException e) {
                System.err.println("Failed to load config file: " + e.getMessage());
                return;
            }
        } else if (args.length >= 1 && !args[0].startsWith("--")) {
            // Legacy mode: positional arguments
            System.out.println("Using legacy CLI arguments (eventID, forecastMin, forecastMax)");
            config = createDefaultConfig();
            config.eventId = args[0];
            if (args.length >= 2)
                config.forecastWindow.minDays = Double.parseDouble(args[1]);
            if (args.length >= 3)
                config.forecastWindow.maxDays = Double.parseDouble(args[2]);
        } else {
            // No args: use default config file if exists, else use hardcoded defaults
            java.io.File defaultConfigFile = new java.io.File("etas_config.json");
            if (defaultConfigFile.exists()) {
                System.out.println("Loading default config from: etas_config.json");
                try {
                    config = ETASConfig.loadFromFile("etas_config.json");
                } catch (IOException e) {
                    System.err.println("Failed to load default config: " + e.getMessage());
                    config = createDefaultConfig();
                }
            } else {
                System.out.println("No config file found. Using hardcoded defaults.");
                config = createDefaultConfig();
            }
        }

        runETAS(config);
    }

    private static ETASConfig createDefaultConfig() {
        ETASConfig c = new ETASConfig();
        c.eventId = "2016p858000";
        c.dataSource = "geonet";

        c.dataWindow = new ETASConfig.WindowConfig();
        c.dataWindow.minDays = 0;
        c.dataWindow.maxDays = 7;

        c.forecastWindow = new ETASConfig.WindowConfig();
        c.forecastWindow.minDays = 7;
        c.forecastWindow.maxDays = 14;

        c.region = new ETASConfig.RegionConfig();
        c.region.radiusKm = 200;
        c.region.minDepth = -10;
        c.region.maxDepth = 100;

        c.catalog = new ETASConfig.CatalogConfig();
        c.catalog.magComplete = 3.0;
        c.catalog.forecastMagnitudes = new double[] { 3.0, 4.0, 5.0 };

        c.priors = new ETASConfig.PriorsConfig();
        c.priors.aMean = -2.423;
        c.priors.aSigma = 0.395;
        c.priors.pMean = 1.08;
        c.priors.pSigma = 0.2;
        c.priors.cMean = 0.01;
        c.priors.logcSigma = 0.7;
        c.priors.alpha = 1.0;
        c.priors.b = 1.0;
        c.priors.refMag = 4.5;

        c.gridSearch = new ETASConfig.GridSearchConfig();
        c.gridSearch.amsMin = -4.0;
        c.gridSearch.amsMax = 1.0;
        c.gridSearch.amsN = 21;
        c.gridSearch.aMin = -3.5;
        c.gridSearch.aMax = -0.5;
        c.gridSearch.aN = 21;
        c.gridSearch.pMin = 0.5;
        c.gridSearch.pMax = 2.0;
        c.gridSearch.pN = 16;
        c.gridSearch.cMin = 1e-4;
        c.gridSearch.cMax = 1e-1;
        c.gridSearch.cN = 16;

        c.simulation = new ETASConfig.SimulationConfig();
        c.simulation.nSims = 100;
        c.simulation.maxGenerations = 10;
        c.simulation.maxMag = 9.5;
        c.simulation.timeDependentMc = false;
        c.simulation.fitMSProductivity = true;

        c.output = new ETASConfig.OutputConfig();
        c.output.summaryFile = "nz_etas_simulations.txt";
        c.output.catalogDir = "simulated_catalogs";

        return c;
    }

    private static void runETAS(ETASConfig config) {
        System.out.println("\n--- Configuration ---");
        System.out.println("Event ID: " + config.eventId);
        System.out.println("Data Window: Day " + config.dataWindow.minDays + " to Day " + config.dataWindow.maxDays);
        System.out.println(
                "Forecast Window: Day " + config.forecastWindow.minDays + " to Day " + config.forecastWindow.maxDays);
        System.out.println("Mag Complete: " + config.catalog.magComplete);
        System.out.println("Simulations: " + config.simulation.nSims);

        // --- Set Random Seed for Reproducibility ---
        if (config.simulation.seed != null) {
            org.opensha.oaf.etas.ETAScatalog.setSeed(config.simulation.seed);
            System.out.println("Random Seed: " + config.simulation.seed);
        } else {
            System.out.println("Random Seed: (not set - non-reproducible)");
        }

        // --- Fetch Data ---
        ETAS_GeoNetAccessor accessor = new ETAS_GeoNetAccessor();

        System.out.println("\nFetching mainshock metadata for " + config.eventId + "...");
        ObsEqkRupture mainshock = accessor.fetchEvent(config.eventId);

        if (mainshock == null) {
            System.err.println("Could not fetch event " + config.eventId);
            return;
        }

        System.out
                .println("Mainshock: M" + mainshock.getMag() + " at " + new java.util.Date(mainshock.getOriginTime()));
        System.out.println("Location: " + mainshock.getHypocenterLocation());

        // --- Fetch Aftershocks ---
        Location centroid = mainshock.getHypocenterLocation();
        SphLatLon sphCentroid = new SphLatLon(centroid);
        SphRegion region = SphRegion.makeCircle(sphCentroid, config.region.radiusKm);

        System.out.println("Fetching aftershocks for data window...");
        ObsEqkRupList aftershocks = accessor.fetchAftershocks(mainshock,
                config.dataWindow.minDays, config.dataWindow.maxDays,
                config.region.minDepth, config.region.maxDepth, region);

        System.out.println("Fetched " + aftershocks.size() + " aftershocks.");

        // --- Filter by Mc ---
        ObsEqkRupList filteredAftershocks = new ObsEqkRupList();
        for (ObsEqkRupture rup : aftershocks) {
            if (rup.getMag() >= config.catalog.magComplete) {
                filteredAftershocks.add(rup);
            }
        }
        System.out.println("Aftershocks >= Mc(" + config.catalog.magComplete + "): " + filteredAftershocks.size());

        // --- Setup Prior Model ---
        GenericETAS_Parameters nzParams = new GenericETAS_Parameters(
                config.priors.aMean, config.priors.aSigma,
                config.priors.pMean, config.priors.pSigma,
                config.priors.cMean, config.priors.logcSigma,
                7.13E-06, 7.67E-06, 8.99E-04, 2.63E-06, 3.75E-05, 4.50E-05, 2300,
                config.priors.alpha, config.priors.b, config.priors.refMag);

        ETAS_AftershockModel_Generic priorModel = new ETAS_AftershockModel_Generic(
                mainshock, filteredAftershocks, nzParams,
                config.dataWindow.minDays, config.dataWindow.maxDays,
                config.forecastWindow.minDays, config.forecastWindow.maxDays,
                config.catalog.magComplete, config.simulation.maxMag,
                config.simulation.maxGenerations, config.simulation.nSims,
                false, config.simulation.timeDependentMc, null, false);

        // --- Grid Search Vectors ---
        double[] amsVec = ETAS_StatsCalc.linspace(config.gridSearch.amsMin, config.gridSearch.amsMax,
                config.gridSearch.amsN);
        double amsSigma = 0.5;
        double[] aVec = ETAS_StatsCalc.linspace(config.gridSearch.aMin, config.gridSearch.aMax, config.gridSearch.aN);
        double[] pVec = ETAS_StatsCalc.linspace(config.gridSearch.pMin, config.gridSearch.pMax, config.gridSearch.pN);
        double[] cVec = ETAS_StatsCalc.logspace(config.gridSearch.cMin, config.gridSearch.cMax, config.gridSearch.cN);

        // --- Run Sequence Specific Model ---
        System.out.println("\nComputing sequence-specific ETAS model...");
        ETAS_AftershockModel_SequenceSpecific seqModel = new ETAS_AftershockModel_SequenceSpecific(
                mainshock, filteredAftershocks,
                amsVec, amsSigma, aVec, pVec, cVec,
                config.priors.alpha, config.priors.b, config.priors.refMag,
                config.dataWindow.minDays, config.dataWindow.maxDays,
                config.forecastWindow.minDays, config.forecastWindow.maxDays,
                config.catalog.magComplete, config.simulation.maxMag,
                config.simulation.maxGenerations, config.simulation.nSims,
                config.simulation.fitMSProductivity, config.simulation.timeDependentMc,
                priorModel, null, false);

        // --- Output Results ---
        DecimalFormat df = new DecimalFormat("0.0000");
        System.out.println("\n--- ETAS Results ---");
        System.out.println("ams-value (Mainshock Productivity): " + df.format(seqModel.getMaxLikelihood_ams()));
        System.out.println("a-value (Aftershock Productivity): " + df.format(seqModel.getMaxLikelihood_a()));
        System.out.println("p-value: " + df.format(seqModel.getMaxLikelihood_p()));
        System.out.println("c-value: " + df.format(seqModel.getMaxLikelihood_c()));
        System.out.println("b-value: " + df.format(seqModel.get_b()));

        // --- Forecast ---
        double rateMc = seqModel.getExpectedNumEvents(config.catalog.magComplete,
                config.forecastWindow.minDays, config.forecastWindow.maxDays);
        double bVal = seqModel.get_b();
        double Mc = config.catalog.magComplete;

        // Use configurable forecast magnitudes (default to [3,4,5] if not specified)
        double[] forecastMags = config.catalog.forecastMagnitudes;
        if (forecastMags == null || forecastMags.length == 0) {
            forecastMags = new double[] { 3.0, 4.0, 5.0 };
        }

        double[] forecastRates = new double[forecastMags.length];
        double[] forecastProbs = new double[forecastMags.length];

        System.out.println(
                "\nForecast (Days " + config.forecastWindow.minDays + "-" + config.forecastWindow.maxDays + "):");
        for (int i = 0; i < forecastMags.length; i++) {
            forecastRates[i] = rateMc * Math.pow(10, -bVal * (forecastMags[i] - Mc));
            forecastProbs[i] = 1.0 - Math.exp(-forecastRates[i]);
            System.out.println("M>=" + forecastMags[i] + ": " + df.format(forecastRates[i]));
        }

        // --- Probability ---
        System.out.println("\nProbability of >=1 event:");
        for (int i = 0; i < forecastMags.length; i++) {
            System.out.println("M>=" + forecastMags[i] + ": " + df.format(forecastProbs[i] * 100) + "%");
        }

        // --- Observed Count ---
        System.out.println("\n--- Observed Aftershocks ---");
        ObsEqkRupList forecastWindowAftershocks = accessor.fetchAftershocks(mainshock,
                config.forecastWindow.minDays, config.forecastWindow.maxDays,
                config.region.minDepth, config.region.maxDepth, region);

        int[] observedCounts = new int[forecastMags.length];
        for (ObsEqkRupture r : forecastWindowAftershocks) {
            for (int i = 0; i < forecastMags.length; i++) {
                if (r.getMag() >= forecastMags[i])
                    observedCounts[i]++;
            }
        }
        for (int i = 0; i < forecastMags.length; i++) {
            System.out.println("Observed M>=" + forecastMags[i] + ": " + observedCounts[i]);
        }

        // --- Export ---
        try {
            java.io.File file = new java.io.File(config.output.summaryFile);
            java.io.PrintWriter pw = new java.io.PrintWriter(file);

            pw.println("ETAS Forecast Results");
            pw.println("=====================");
            pw.println("Event: " + config.eventId);
            pw.println("Analysis Date: " + new java.util.Date());
            pw.println("Mag Complete (Mc): " + config.catalog.magComplete);
            pw.println("Num Simulations: " + config.simulation.nSims);
            pw.println();
            pw.println("--- Fitted Parameters ---");
            pw.println("ams-value: " + df.format(seqModel.getMaxLikelihood_ams()));
            pw.println("a-value: " + df.format(seqModel.getMaxLikelihood_a()));
            pw.println("p-value: " + df.format(seqModel.getMaxLikelihood_p()));
            pw.println("c-value: " + df.format(seqModel.getMaxLikelihood_c()));
            pw.println("b-value: " + df.format(seqModel.get_b()));
            pw.println();
            pw.println("--- Forecast (Days " + config.forecastWindow.minDays + "-" + config.forecastWindow.maxDays
                    + ") ---");
            pw.println("Expected Number of Events:");
            for (int i = 0; i < forecastMags.length; i++) {
                pw.println("  M>=" + forecastMags[i] + ": " + df.format(forecastRates[i]));
            }
            pw.println();
            pw.println("Probability of >=1 Event:");
            for (int i = 0; i < forecastMags.length; i++) {
                pw.println("  M>=" + forecastMags[i] + ": " + df.format(forecastProbs[i] * 100) + "%");
            }
            pw.println();

            // --- Uncertainty from Simulations ---
            pw.println("--- Uncertainty (from " + config.simulation.nSims + " simulations) ---");
            pw.println("Percentiles of event counts in forecast window:");
            for (int magIdx = 0; magIdx < forecastMags.length; magIdx++) {
                double magThreshold = forecastMags[magIdx];
                // Use built-in OpenSHA method for fractile calculation
                double p5 = seqModel.getFractileNumEvents(magThreshold,
                        config.forecastWindow.minDays, config.forecastWindow.maxDays, 0.05);
                double p50 = seqModel.getFractileNumEvents(magThreshold,
                        config.forecastWindow.minDays, config.forecastWindow.maxDays, 0.50);
                double p95 = seqModel.getFractileNumEvents(magThreshold,
                        config.forecastWindow.minDays, config.forecastWindow.maxDays, 0.95);
                pw.println("  M>=" + magThreshold + ":  5th=" + (int) p5 + "  Median=" + (int) p50 + "  95th="
                        + (int) p95);
            }
            pw.println();
            pw.println("--- Simulated Catalogs ---");
            pw.println("Saved to directory: " + config.output.catalogDir);
            pw.close();

            System.out.println("\nSummary saved to: " + file.getAbsolutePath());

            // --- Export Catalogs ---
            if (seqModel.getSimulatedCatalog() != null) {
                java.io.File simDir = new java.io.File(config.output.catalogDir);
                if (!simDir.exists())
                    simDir.mkdir();

                System.out.println("Writing " + config.simulation.nSims + " simulation files...");
                for (int i = 0; i < config.simulation.nSims; i++) {
                    String fileName = String.format("sim_%04d.txt", (i + 1));
                    java.io.File simFile = new java.io.File(simDir, fileName);
                    java.io.PrintWriter simPw = new java.io.PrintWriter(simFile);
                    simPw.println("# Simulation " + (i + 1));
                    simPw.println("# RelativeTime(days) Magnitude Generation");
                    String catStr = seqModel.getSimulatedCatalog().printCatalog(i);
                    simPw.print(catStr);
                    simPw.close();
                }
                System.out.println("Done.");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
