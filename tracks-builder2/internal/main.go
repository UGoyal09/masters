// Package internal contains the core part of the program
package internal

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strings"

	"github.com/MaritimeOptima/cabinet"
	"github.com/MaritimeOptima/services/ais-collector/pkg/aisdb"
	"github.com/MaritimeOptima/services/pkg/db/postgres"
	"github.com/MaritimeOptima/services/pkg/errutils"
	trackproto "github.com/MaritimeOptima/services/protobuf/build/go/services/tracks"
	"github.com/MaritimeOptima/services/tracks/pkg/tracks"
	"github.com/MaritimeOptima/voyage-predictions/tracks-builder2/internal/config"
	"github.com/MaritimeOptima/voyage-predictions/tracks-builder2/internal/models"
	"github.com/MaritimeOptima/voyage-predictions/tracks-builder2/pkg/utils"
	"github.com/paulmach/orb"
	"github.com/paulmach/orb/geo"
	"github.com/sirupsen/logrus"
	"github.com/twpayne/go-geom"
	"github.com/twpayne/go-geom/encoding/wkt"
	"google.golang.org/grpc/codes"
)

type TracksBuilder struct {
	DB *postgres.Instance
}

// Init initializes the databases
func Init(cfg *config.Config) TracksBuilder {
	// initialize databases
	db := cfg.DB.Postgres("", "tracks-builder", cfg.Environment)
	// you might need this if you get an error on start
	db.ConnectionString = strings.ReplaceAll(db.ConnectionString, "\n", "")

	return TracksBuilder{
		DB: db,
	}
}

// Start the application
func Start(cfg *config.Config) {
	tb := Init(cfg)
	ctx := context.Background()

	// Start DBs
	errutils.MustExplain(tb.DB.Start(), "Started AIS database instance")
	defer utils.Check(tb.DB.Close)

	cab, err := cabinet.NewAzureAuthenticated(cfg.AzBlob.AccountName, cfg.AzBlob.AccountKey, cfg.Bucket)
	errutils.MustExplain(err, "Create Azure storage instance")

	voyageTimes, err := tb.getVoyageTimes()
	errutils.MustExplain(err, "failed at getting voyage times")

	trackMap, err := tb.getVoyageTracks(voyageTimes, cab)
	errutils.MustExplain(err, "error getting track points")

	logrus.Info("inserting trajectories to db")
	err = tb.DB.RunInTxx(ctx, nil, func(tx *postgres.TX) error {
		return models.UpdateTrajectoriesByIDs(tx, trackMap)
	})
	errutils.MustExplain(err, "error updating tracks")
}

func (tb *TracksBuilder) getVoyageTracks(voyageTimes []models.VoyageTime, cab *cabinet.Instance) (map[int64]string, error) {
	ctx := context.Background()
	logrus.Info("fetching tracks for voyages")

	trackMap := make(map[int64]string)

	err := tb.DB.RunInTxx(ctx, nil, func(tx *postgres.TX) error {
		for i, vt := range voyageTimes {
			utils.PrintProgress("getVoyageTracks", i, len(voyageTimes))

			// Get MMSI-IMO mapping interval betweeen departure and arrival
			var intervals []aisdb.MMSIInInterval
			err := tb.DB.RunInTxx(ctx, nil, func(tx *postgres.TX) error {
				var err error
				intervals, err = aisdb.GetHistoricMMSIIMOMappings(ctx, tx, vt.IMO, vt.DepartureTimestamp, vt.ArrivalTimestamp)
				return err
			})
			if err != nil {
				return errutils.LogCtxError(ctx, err, codes.Internal, "failed to get historic mapping intervals for tracks")
			}

			if len(intervals) == 0 {
				errutils.CtxLog(ctx).WithField("imo", vt.IMO).Warn("could not find historic mapping for imo")
				return nil
			}

			track, err := tracks.GetTrackPointsIMOMappings(ctx, cab, intervals)
			if err != nil {
				return errutils.LogCtxError(ctx, err, codes.Internal, "failed to get tracks for vessel")
			}

			linestring, err := buildTrajectory(track)
			if err != nil {
				logrus.Infof("%+v", vt)
				logrus.Warn(err)
				continue
			}

			trackMap[vt.ID] = linestring
		}
		return nil
	})
	fmt.Println()

	return trackMap, err
}

// buildTrajectory builds a trajectory from vessel_positions_history rows
// it returns err if a segment of the line is too long
func buildTrajectory(positions []*trackproto.TrackPoint) (string, error) {
	if len(positions) < 2 {
		return "", errors.New("too few points for valid trajectory")
	}

	// allocate array with room for all positions
	trajectoryCoords := make([]geom.Coord, 0, len(positions))

	for i := 0; i < len(positions); i++ {
		current := positions[i]
		// add first coord to trajectory list
		geomCoord := geom.Coord{float64(current.Longitude), float64(current.Latitude)}
		trajectoryCoords = append(trajectoryCoords, geomCoord)

		// find the next valid position and jump to it
		nextPointIndex, err := nextValidPoint(i, 4, positions)
		if err != nil {
			return "", err
		}
		if nextPointIndex != -1 {
			i = nextPointIndex - 1
		}
	}

	trajectory, err := geom.NewLineString(geom.XY).SetCoords(trajectoryCoords)
	if err != nil {
		return "", err
	}

	return wkt.Marshal(trajectory)
}

// nextValidPoint returns the index of the next valid point checking distances to every point within tolerance
// if no valid distances were found wihin tolerance it returns error
// if the last point in trajectory was reached, -1 is returned
func nextValidPoint(start, tolerance int, positions []*trackproto.TrackPoint) (int, error) {
	a := positions[start]
	for j := start + 1; j <= start+tolerance; j++ {
		if j >= len(positions) {
			// if we have checked all points in trajectory
			return -1, nil
		}

		n := positions[j]
		dist := geo.DistanceHaversine(orb.Point{float64(a.Longitude), float64(a.Latitude)}, orb.Point{float64(n.Longitude), float64(n.Latitude)})
		timeDiff := math.Abs(float64(n.Timestamp - a.Timestamp)) // abs incase not sorted, but it should be

		// calculate the required speed to reach the given point with the given time difference
		// times 1.94385 to konvert m/s to knots
		requiredSpeed := (dist / timeDiff) * 1.94385
		// if required speed was more than 50kt, move on to next point
		if requiredSpeed < 50.0 {
			return j, nil
		}
	}

	// no reasonable distances were found within tolerance
	return -1, errors.New("trajectory segment too noisy")
}

func (tb *TracksBuilder) getVoyageTimes() (result []models.VoyageTime, err error) {
	ctx := context.Background()

	err = tb.DB.RunInTxx(ctx, nil, func(tx *postgres.TX) error {
		var err error
		result, err = models.GetVoyagesToBuild(tx)
		return err
	})

	return result, err
}
