package org.opensha.oaf.etas.examples;

import java.text.DecimalFormat;
import org.opensha.commons.geo.Location;
import org.opensha.commons.geo.Region;
import org.opensha.oaf.etas.ETAS_AftershockModel_Generic;
import org.opensha.oaf.etas.ETAS_AftershockModel_SequenceSpecific;
import org.opensha.oaf.etas.ETAS_ComcatAccessor;
import org.opensha.oaf.etas.ETAS_StatsCalc;
import org.opensha.oaf.etas.GenericETAS_Parameters;
import org.opensha.oaf.util.SphLatLon;
import org.opensha.oaf.util.SphRegion;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupList;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupture;
import org.opensha.oaf.etas.ETAS_GeoNetAccessor;

public class ETAS_Demo_NZ {

    public static void main(String[] args) {
        System.out.println("ETAS Demo (NZ): Fetching data from GeoNet and running model...");

        // --- CLI Arguments ---
        // Usage: ETAS_Demo_NZ [eventID] [forecastMinDays] [forecastMaxDays]
        String eventID = "2016p858000"; // Default: Kaikoura 2016 M7.8
        double forecastMinDaysArg = 7.0;
        double forecastMaxDaysArg = 14.0;

        if (args.length >= 1)
            eventID = args[0];
        if (args.length >= 2)
            forecastMinDaysArg = Double.parseDouble(args[1]);
        if (args.length >= 3)
            forecastMaxDaysArg = Double.parseDouble(args[2]);

        final double forecastMinDays = forecastMinDaysArg;
        final double forecastMaxDays = forecastMaxDaysArg;

        System.out.println("Event ID: " + eventID);
        System.out.println("Forecast Window: Day " + forecastMinDays + " to Day " + forecastMaxDays);

        // Use GeoNet Custom Accessor
        ETAS_GeoNetAccessor accessor = new ETAS_GeoNetAccessor();

        System.out.println("Fetching mainshock metadata for " + eventID + "...");
        ObsEqkRupture mainshock = accessor.fetchEvent(eventID);

        if (mainshock == null) {
            System.err.println("Could not fetch event " + eventID);
            return;
        }

        System.out
                .println("Mainshock: M" + mainshock.getMag() + " at " + new java.util.Date(mainshock.getOriginTime()));
        System.out.println("Location: " + mainshock.getHypocenterLocation());

        // 2. Fetch Aftershocks
        // Fetch 7 days of aftershocks
        double minDays = 0;
        double maxDays = 7.0;
        double minDepth = -10.0;
        double maxDepth = 100.0;

        // Define a region around the mainshock
        // Kaikoura rupture was long (~150km), so we need a large radius.
        Location centroid = mainshock.getHypocenterLocation();
        SphLatLon sphCentroid = new SphLatLon(centroid);
        // Using 200km radius to capture the full rupture area and aftershock zone
        SphRegion region = SphRegion.makeCircle(sphCentroid, 200.0);

        System.out.println("Fetching aftershocks for 7 days...");
        ObsEqkRupList aftershocks = accessor.fetchAftershocks(mainshock, minDays, maxDays, minDepth, maxDepth, region);

        System.out.println("Fetched " + aftershocks.size() + " aftershocks.");

        // 3. Setup Model Parameters
        double magComplete = 2.95; // Higher Mc for automated catalog in this complex processing? Or standard 2.5?
        // Let's stick with 3.0 to be safe and robust.
        magComplete = 3.0;

        // Check for duplicates
        java.util.Set<String> ids = new java.util.HashSet<>();
        int duplicates = 0;
        for (ObsEqkRupture r : aftershocks) {
            if (ids.contains(r.getEventId()))
                duplicates++;
            else
                ids.add(r.getEventId());
        }
        System.out.println("Duplicate events found: " + duplicates);

        // FILTER: We must filter the aftershocks to magComplete, otherwise the model
        // uses micros
        // to fit parameters but assumes they are above Mc, leading to massive
        // over-prediction.
        ObsEqkRupList filteredAftershocks = new ObsEqkRupList();
        for (ObsEqkRupture rup : aftershocks) {
            if (rup.getMag() >= magComplete) {
                filteredAftershocks.add(rup);
            }
        }
        System.out.println("Aftershocks >= Mc(" + magComplete + "): " + filteredAftershocks.size());

        // Use standard generic parameters as prior since we don't have explicit NZ
        // prior loaded yet
        GenericETAS_Parameters genericParams = new GenericETAS_Parameters();

        // Define simulation/fit parameters
        // double forecastMinDays = 7.0; // Now from CLI
        // double forecastMaxDays = 14.0; // Now from CLI
        double maxSimMag = 9.5;
        int maxNumGenerations = 10;
        int nSims = 100;
        boolean fitMSProductivity = true;
        boolean timeDependentMc = false; // Set to true for early sequences

        // Initialize Prior Model (Generic)
        // Initialize Prior Model (Generic)
        // Using "Active Shallow Crust" (ANSR) proxy values from OAF OETAS CSV:
        // p=1.08, c=0.01, a~-2.4 (default).
        // We reuse default covariances/sigmas from the generic model but tune the
        // means.

        // Defaults from GenericETAS_Parameters source:
        // aMean=-2.423, aSigma=0.395, pMean=0.966, pSigma=0.2, cMean=0.0027...
        // We update pMean to 1.08 and cMean to 0.01.
        GenericETAS_Parameters nzParams = new GenericETAS_Parameters(
                -2.423, 0.395,
                1.08, 0.2,
                0.01, 0.7,
                7.13E-06, 7.67E-06, 8.99E-04, 2.63E-06, 3.75E-05, 4.50E-05, 2300,
                1.0, 1.0, 4.5);

        ETAS_AftershockModel_Generic priorModel = new ETAS_AftershockModel_Generic(
                mainshock,
                filteredAftershocks,
                nzParams,
                minDays, maxDays, forecastMinDays, forecastMaxDays,
                magComplete, maxSimMag, maxNumGenerations, nSims,
                false,
                timeDependentMc,
                null,
                false);

        // Define Grid Search Vectors
        double[] amsVec = ETAS_StatsCalc.linspace(-4.0, 1.0, 21);
        double amsSigma = 0.5;
        double[] aVec = ETAS_StatsCalc.linspace(-3.5, -0.5, 21);
        double[] pVec = ETAS_StatsCalc.linspace(0.5, 2.0, 16);
        double[] cVec = ETAS_StatsCalc.logspace(1e-4, 1e-1, 16);

        double alpha = genericParams.get_alpha();
        double b = genericParams.get_b();
        double refMag = genericParams.get_refMag();

        // 4. Run Sequence Specific Model
        System.out.println("Computing sequence-specific ETAS model...");
        ETAS_AftershockModel_SequenceSpecific seqModel = new ETAS_AftershockModel_SequenceSpecific(
                mainshock,
                filteredAftershocks,
                amsVec, amsSigma,
                aVec,
                pVec,
                cVec,
                alpha, b, refMag,
                minDays, maxDays, forecastMinDays, forecastMaxDays,
                magComplete, maxSimMag, maxNumGenerations, nSims,
                fitMSProductivity,
                timeDependentMc,
                priorModel,
                null,
                false);

        // 5. Output Results
        DecimalFormat df = new DecimalFormat("0.0000");
        System.out.println("\n--- ETAS Results (NZ/GeoNet) ---");
        System.out.println("ams-value (Mainshock Productivity): " + df.format(seqModel.getMaxLikelihood_ams()));
        System.out.println("a-value (Aftershock Productivity): " + df.format(seqModel.getMaxLikelihood_a()));
        System.out.println("p-value: " + df.format(seqModel.getMaxLikelihood_p()));
        System.out.println("c-value: " + df.format(seqModel.getMaxLikelihood_c()));
        System.out.println("b-value (model): " + df.format(seqModel.get_b()));

        // Check MagStats
        double minMagFound = 10.0;
        double maxMagFound = -10.0;
        double sumMag = 0;
        for (ObsEqkRupture r : filteredAftershocks) {
            double m = r.getMag();
            if (m < minMagFound)
                minMagFound = m;
            if (m > maxMagFound)
                maxMagFound = m;
            sumMag += m;
        }
        System.out.println("Filtered Mags: Min=" + minMagFound + " Max=" + maxMagFound + " Avg="
                + (sumMag / filteredAftershocks.size()));

        // Forecast
        // NOTE: getExpectedNumEvents returns the total number of events >= magComplete.
        // It does NOT scale the output to magMin (it uses magMin only to filter
        // triggers).
        // We must apply Gutenberg-Richter scaling manually: N(>=M) = N(>=Mc) *
        // 10^(-b*(M-Mc))

        System.out.println("\nForecast for days 7-14:");

        double rateMc = seqModel.getExpectedNumEvents(magComplete, forecastMinDays, forecastMaxDays);
        double bVal = seqModel.get_b();

        double n3 = rateMc * Math.pow(10, -bVal * (3.0 - magComplete));
        double n4 = rateMc * Math.pow(10, -bVal * (4.0 - magComplete));
        double n5 = rateMc * Math.pow(10, -bVal * (5.0 - magComplete));

        System.out.println("M>=3.0: " + df.format(n3));
        System.out.println("M>=4.0: " + df.format(n4));
        System.out.println("M>=5.0: " + df.format(n5));

        // --- Probability of >=1 Event ---
        double prob4 = 1.0 - Math.exp(-n4);
        double prob5 = 1.0 - Math.exp(-n5);
        System.out.println("\nProbability of >=1 event:");
        System.out.println("M>=4.0: " + df.format(prob4 * 100) + "%");
        System.out.println("M>=5.0: " + df.format(prob5 * 100) + "%");

        // --- Observed Count for Validation ---
        // Fetch aftershocks for the forecast window to compare
        System.out.println("\n--- Observed Aftershocks (Days " + forecastMinDays + "-" + forecastMaxDays + ") ---");
        ObsEqkRupList forecastWindowAftershocks = accessor.fetchAftershocks(mainshock, forecastMinDays, forecastMaxDays,
                minDepth, maxDepth, region);
        int obs3 = 0, obs4 = 0, obs5 = 0;
        for (ObsEqkRupture r : forecastWindowAftershocks) {
            if (r.getMag() >= 3.0)
                obs3++;
            if (r.getMag() >= 4.0)
                obs4++;
            if (r.getMag() >= 5.0)
                obs5++;
        }
        System.out.println("Observed M>=3.0: " + obs3);
        System.out.println("Observed M>=4.0: " + obs4);
        System.out.println("Observed M>=5.0: " + obs5);

        // --- Export Results to File ---
        try {
            java.io.File file = new java.io.File("nz_etas_simulations.txt");
            java.io.PrintWriter pw = new java.io.PrintWriter(file);

            pw.println("ETAS Forecast Results (Kaikoura 2016)");
            pw.println("=====================================");
            pw.println("Analysis Date: " + new java.util.Date());
            pw.println("Mag Complete (Mc): " + magComplete);
            pw.println("Num Simulations: " + nSims);
            pw.println();

            pw.println("--- Fitted Parameters ---");
            pw.println("a-value: " + df.format(seqModel.getMaxLikelihood_a()));
            pw.println("p-value: " + df.format(seqModel.getMaxLikelihood_p()));
            pw.println("c-value: " + df.format(seqModel.getMaxLikelihood_c()));
            pw.println("b-value: " + df.format(seqModel.get_b()));
            pw.println("alpha:   " + df.format(genericParams.get_alpha()));
            pw.println();

            pw.println("--- Forecast (Days " + forecastMinDays + "-" + forecastMaxDays + ") ---");
            pw.println("M>=3.0: " + df.format(n3));
            pw.println("M>=4.0: " + df.format(n4));
            pw.println("M>=5.0: " + df.format(n5));
            pw.println();

            pw.println("--- Simulated Catalogs ---");
            pw.println("Saved 100 catalogs to directory: simulated_catalogs/");

            pw.close();
            System.out.println("\nSummary results saved to: " + file.getAbsolutePath());

            // --- Export Separate Simulation Files ---
            if (seqModel.getSimulatedCatalog() != null) {
                java.io.File simDir = new java.io.File("simulated_catalogs");
                if (!simDir.exists())
                    simDir.mkdir();

                System.out.println("Writing " + nSims + " simulation files to " + simDir.getName() + "...");

                for (int i = 0; i < nSims; i++) {
                    String fileName = String.format("sim_%04d.txt", (i + 1));
                    java.io.File simFile = new java.io.File(simDir, fileName);
                    java.io.PrintWriter simPw = new java.io.PrintWriter(simFile);

                    // Optional Header
                    simPw.println("# Simulation " + (i + 1));
                    simPw.println("# RelativeTime(days) Magnitude Generation");

                    String catStr = seqModel.getSimulatedCatalog().printCatalog(i);
                    simPw.print(catStr); // printCatalog already includes newlines
                    simPw.close();
                }
                System.out.println("Done.");
            } else {
                System.out.println("No simulated catalogs available to write.");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
