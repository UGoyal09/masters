package models

import (
	"time"

	"github.com/MaritimeOptima/services/pkg/db/postgres"
	"github.com/MaritimeOptima/services/pkg/errutils"
	"github.com/MaritimeOptima/voyage-predictions/tracks-builder2/pkg/utils"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc/codes"
)

type VoyageTime struct {
	ID                 int64     `db:"id"`
	IMO                int64     `db:"imo"`
	ArrivalTimestamp   time.Time `db:"arrival_timestamp"`
	DepartureTimestamp time.Time `db:"departure_timestamp"`
	Segment            string    `db:"segment"`
}

// GetVoyagesToBuild fetches voyages without trajectories.
func GetVoyagesToBuild(tx *postgres.TX) ([]VoyageTime, error) {
	logrus.Info("fetching last voyage for each vessel in voyages")

	var voyages []VoyageTime
	q := `
        SELECT
            id,
            imo,
            arrival_timestamp,
            departure_timestamp
        FROM
            "voyages"

		where 
			segment='container'

		ORDER By
			id
    `

	err := tx.Tx.Select(&voyages, q)
	if err != nil {
		return nil, errutils.NewModelError(codes.Internal, err, "failed to select transitions")
	}

	return voyages, nil
}

func UpdateTrajectoriesByIDs(tx *postgres.TX, trackMap map[int64]string) error {
	q := `
        UPDATE "voyages"
        SET trajectory = $2
        WHERE id=$1
    `

	i := 1
	for id, track := range trackMap {
		utils.PrintProgress("UpdateTrajectoriesByIDs", i, len(trackMap))
		_, err := tx.Tx.Exec(q, id, track)
		if err != nil {
			return errutils.NewModelError(codes.Internal, err, "failed to select transitions")
		}
		i++
	}

	return nil
}
