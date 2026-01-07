package org.opensha.oaf.etas;

import java.io.InputStream;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.opensha.commons.geo.Location;
import org.opensha.oaf.util.SphRegion;
import org.opensha.oaf.util.catalog.ObsEqkRupEventIdComparator;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupList;
import org.opensha.sha.earthquake.observedEarthquake.ObsEqkRupture;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/**
 * Accessor for GeoNet FDSN Web Service which returns QuakeML (XML).
 */
public class ETAS_GeoNetAccessor {

    private static final String BASE_URL = "https://service.geonet.org.nz/fdsnws/event/1/query";

    public ETAS_GeoNetAccessor() {
    }

    public ObsEqkRupture fetchEvent(String eventID) {
        try {
            String urlStr = BASE_URL + "?eventid=" + URLEncoder.encode(eventID, StandardCharsets.UTF_8.toString());
            System.out.println("Fetching event: " + urlStr);

            InputStream is = new URL(urlStr).openStream();

            ObsEqkRupList events = parseQuakeML(is);
            if (events.isEmpty())
                return null;

            return events.get(0);

        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public ObsEqkRupList fetchAftershocks(ObsEqkRupture mainshock, double minDays, double maxDays,
            double minDepth, double maxDepth, SphRegion region) {

        try {
            long eventTime = mainshock.getOriginTime();
            String startTime = Instant.ofEpochMilli(eventTime + (long) (minDays * 86400000L)).toString();
            String endTime = Instant.ofEpochMilli(eventTime + (long) (maxDays * 86400000L)).toString();

            StringBuilder urlBuilder = new StringBuilder(BASE_URL);
            urlBuilder.append("?starttime=").append(startTime);
            urlBuilder.append("&endtime=").append(endTime);
            urlBuilder.append("&mindepth=").append(minDepth);
            urlBuilder.append("&maxdepth=").append(maxDepth);

            // Region
            if (region.isCircular()) {
                urlBuilder.append("&latitude=").append(String.format("%.5f", region.getCircleCenter().get_lat()));
                urlBuilder.append("&longitude=").append(String.format("%.5f", region.getCircleCenter().get_lon()));
                urlBuilder.append("&maxradius=").append(String.format("%.5f", region.getCircleRadiusDeg()));
            } else {
                urlBuilder.append("&minlatitude=").append(String.format("%.5f", region.getMinLat()));
                urlBuilder.append("&maxlatitude=").append(String.format("%.5f", region.getMaxLat()));
                urlBuilder.append("&minlongitude=").append(String.format("%.5f", region.getMinLon()));
                urlBuilder.append("&maxlongitude=").append(String.format("%.5f", region.getMaxLon()));
            }
            // GeoNet can handle large responses, but let's be safe? usually they paginate
            // but FDSN 1.2 standard limit is often 20000
            // GeoNet doesn't strictly enforce limit param in same way or has high limit.

            System.out.println("Fetching aftershocks from: " + urlBuilder.toString());

            InputStream is = new URL(urlBuilder.toString()).openStream();
            ObsEqkRupList rups = parseQuakeML(is);

            // Filter mainshock
            ObsEqkRupList filtered = new ObsEqkRupList();
            for (ObsEqkRupture r : rups) {
                if (!r.getEventId().equals(mainshock.getEventId())) {
                    filtered.add(r);
                }
            }

            filtered.sortByOriginTime();
            return filtered;

        } catch (Exception e) {
            e.printStackTrace();
            return new ObsEqkRupList();
        }
    }

    // Simple QuakeML Parser
    private ObsEqkRupList parseQuakeML(InputStream is) throws Exception {
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
        Document doc = dBuilder.parse(is);
        doc.getDocumentElement().normalize();

        ObsEqkRupList rups = new ObsEqkRupList();
        NodeList eventList = doc.getElementsByTagName("event");

        for (int i = 0; i < eventList.getLength(); i++) {
            Node eventNode = eventList.item(i);
            if (eventNode.getNodeType() == Node.ELEMENT_NODE) {
                Element eventElement = (Element) eventNode;

                String publicID = eventElement.getAttribute("publicID");
                // GeoNet publicIDs often look like "smi:nz.org.geonet/Event/2016p858000" or
                // just "2016p858000"
                // We want the simplified one if possible or just use whatever.
                // But simpler to use the simplified ID if available?

                // Try to find preferred origin and magnitude
                // In simple parsing, we just take the first origin and magnitude or preferred
                // one.

                String preferredOriginID = getTagValue("preferredOriginID", eventElement);
                String preferredMagID = getTagValue("preferredMagnitudeID", eventElement);

                Element origin = findElementByIdOrFirst(eventElement, "origin", "publicID", preferredOriginID);
                Element magnitude = findElementByIdOrFirst(eventElement, "magnitude", "publicID", preferredMagID);

                if (origin != null && magnitude != null) {
                    try {
                        // Time
                        Element timeEl = (Element) origin.getElementsByTagName("time").item(0);
                        String timeStr = getTagValue("value", timeEl);
                        long timeMillis = Instant.parse(timeStr).toEpochMilli();

                        // Location
                        double lat = Double.parseDouble(
                                getTagValue("value", (Element) origin.getElementsByTagName("latitude").item(0)));
                        double lon = Double.parseDouble(
                                getTagValue("value", (Element) origin.getElementsByTagName("longitude").item(0)));
                        double depth = Double.parseDouble(
                                getTagValue("value", (Element) origin.getElementsByTagName("depth").item(0))) / 1000.0; // QuakeML
                                                                                                                        // depth
                                                                                                                        // is
                                                                                                                        // meters?
                                                                                                                        // GeoNet
                                                                                                                        // usually
                                                                                                                        // meters.
                                                                                                                        // check.
                        // GeoNet QuakeML depth is in meters?
                        // <depth><value>15100</value> ...
                        // Yes, usually meters in FDSN. OpenSHA expects km.

                        Location loc = new Location(lat, lon, depth);

                        // Magnitude
                        double mag = Double.parseDouble(
                                getTagValue("value", (Element) magnitude.getElementsByTagName("mag").item(0)));

                        // ID cleanup
                        // If publicID is a URI, extracting the last part might be better but let's keep
                        // it unique.
                        // GeoNet example: smi:nz.org.geonet/Event/2016p858000
                        // Clean ID: 2016p858000
                        String cleanID = publicID;
                        if (publicID.contains("/")) {
                            cleanID = publicID.substring(publicID.lastIndexOf('/') + 1);
                        }

                        ObsEqkRupture rup = new ObsEqkRupture(cleanID, timeMillis, loc, mag);
                        rups.add(rup);
                    } catch (Exception e) {
                        // Error parsing this event, skip
                        // System.err.println("Error parsing event " + publicID);
                    }
                }
            }
        }

        return rups;
    }

    private Element findElementByIdOrFirst(Element parent, String tagName, String idAttr, String idValue) {
        NodeList list = parent.getElementsByTagName(tagName);
        if (list.getLength() == 0)
            return null;

        for (int i = 0; i < list.getLength(); i++) {
            Element el = (Element) list.item(i);
            if (idValue != null && idValue.equals(el.getAttribute(idAttr))) {
                return el;
            }
        }
        return (Element) list.item(0); // Fallback to first
    }

    private String getTagValue(String tag, Element element) {
        NodeList nodeList = element.getElementsByTagName(tag).item(0).getChildNodes();
        Node node = (Node) nodeList.item(0);
        return node.getNodeValue();
    }
}
