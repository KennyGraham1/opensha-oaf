package org.opensha.oaf.etas.examples;

import org.opensha.oaf.etas.ETAS_AftershockModel_Generic;
import org.opensha.oaf.etas.ETAS_AftershockModel_SequenceSpecific;
import org.opensha.oaf.etas.ETAS_ComcatAccessor;
import org.opensha.oaf.etas.ETAS_StatsCalc;
import org.opensha.oaf.util.SphRegion;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupList;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupture;
import org.opensha.commons.geo.Location;
import org.opensha.commons.geo.Region;

import java.util.GregorianCalendar;
import java.text.DecimalFormat;

public class ETAS_Demo {

    public static void main(String[] args) {
        System.out.println("ETAS Demo: Fetching data and running model...");

        // 1. Define the event (Ridgecrest 2019 M7.1)
        String eventID = "ci38457511";

        ETAS_ComcatAccessor accessor = new ETAS_ComcatAccessor();

        System.out.println("Fetching mainshock metadata for " + eventID + "...");
        ObsEqkRupture mainshock = accessor.fetchEvent(eventID, false);

        if (mainshock == null) {
            System.err.println("Could not fetch event " + eventID);
            return;
        }

        System.out
                .println("Mainshock: M" + mainshock.getMag() + " at " + new java.util.Date(mainshock.getOriginTime()));

        // 2. Fetch Aftershocks
        // Fetch 7 days of aftershocks
        double minDays = 0;
        double maxDays = 7.0;
        double minDepth = -10.0;
        double maxDepth = 100.0;

        // Define a region around the mainshock
        Location centroid = mainshock.getHypocenterLocation();
        // Correct usage of SphRegion.makeCircle using SphLatLon
        org.opensha.oaf.util.SphLatLon sphCentroid = new org.opensha.oaf.util.SphLatLon(centroid);
        org.opensha.oaf.util.SphRegion region = SphRegion.makeCircle(sphCentroid, 100.0);

        System.out.println("Fetching aftershocks for 7 days...");
        ObsEqkRupList aftershocks = accessor.fetchAftershocks(mainshock, minDays, maxDays, minDepth, maxDepth, region,
                false);

        System.out.println("Fetched " + aftershocks.size() + " aftershocks.");

        // 3. Setup Model Parameters
        double magComplete = 2.5; // Assumed Mc
        // Use generic California parameters as a prior
        org.opensha.oaf.etas.GenericETAS_Parameters genericParams = new org.opensha.oaf.etas.GenericETAS_Parameters();

        // Define simulation/fit parameters
        double forecastMinDays = 7.0;
        double forecastMaxDays = 14.0;
        double maxSimMag = 9.5;
        int maxNumGenerations = 10;
        int nSims = 100; // Low number for speed
        boolean fitMSProductivity = true;
        boolean timeDependentMc = false;

        // Initialize Prior Model (Generic)
        ETAS_AftershockModel_Generic priorModel = new ETAS_AftershockModel_Generic(
                mainshock,
                aftershocks,
                genericParams,
                minDays, maxDays, forecastMinDays, forecastMaxDays,
                magComplete, maxSimMag, maxNumGenerations, nSims,
                false, // fitMSProductivity (false for prior usually)
                timeDependentMc,
                null, // progress bar
                false // validate
        );

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
                aftershocks,
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
                null, // progress
                false // validate
        );

        // 5. Output Results
        DecimalFormat df = new DecimalFormat("0.0000");
        System.out.println("\n--- ETAS Results ---");
        System.out.println("a-value: " + df.format(seqModel.getMaxLikelihood_a()));
        System.out.println("p-value: " + df.format(seqModel.getMaxLikelihood_p()));
        System.out.println("c-value: " + df.format(seqModel.getMaxLikelihood_c()));

        // Calculate expected number of M>=3 aftershocks in the next week (days 7 to 14)
        double forecastMinMag = 3.0;

        double expectedNum = seqModel.getExpectedNumEvents(forecastMinMag, forecastMinDays, forecastMaxDays);
        System.out.println("\nForecast for days 7-14 (M>=" + forecastMinMag + "):");
        System.out.println("Expected number of events: " + df.format(expectedNum));
    }
}
