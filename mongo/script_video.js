/////////////////////////////////////////
// Índice simple
////////////////////////////////////////
 db.reviews.dropIndex("idx_order_id");

db.reviews.find({
    order_id:
        db.reviews.findOne(
            {},
            { order_id: 1 }
        ).order_id
}).explain("executionStats");

db.reviews.createIndex(
    {
        order_id: 1
    },
    {
        name: "idx_order_id"
    }
);

db.reviews.find({
    order_id:
        db.reviews.findOne(
            {},
            { order_id: 1 }
        ).order_id
}).explain("executionStats");



/////////////////////////////////////////
// Índice compuesto
/////////////////////////////////////////
db.reviews.dropIndex("idx_score_date");

db.reviews.find({
    review_score: 5
})
.sort({
    review_creation_date: -1
})
.explain("executionStats");

db.reviews.createIndex(
    {
        review_score: 1,
        review_creation_date: -1
    },
    {
        name: "idx_score_date"
    }
);

db.reviews.find({
    review_score: 5
})
.sort({
    review_creation_date: -1
})
.explain("executionStats");



/////////////////////////////////////////
//Índice parcial
/////////////////////////////////////////
db.reviews.dropIndex("idx_positive_reviews");

db.reviews.find({
    review_score: {
        $gte: 4
    }
}).explain("executionStats");

db.reviews.createIndex(
    {
        review_score: 1
    },
    {
        name: "idx_positive_reviews",
        partialFilterExpression: {
            review_score: {
                $gte: 4
            }
        }
    }
);

db.reviews.find({
    review_score: {
        $gte: 4
    }
}).explain("executionStats");



/////////////////////////////////////////
//Aggregation Pipeline
/////////////////////////////////////////
db.reviews.dropIndex("idx_review_score");

db.reviews.aggregate([
    {
        $match: {
            review_score: {
                $gte: 4
            }
        }
    },
    {
        $group: {
            _id: "$review_score",
            total: {
                $sum: 1
            }
        }
    }
]).explain("executionStats");

db.reviews.createIndex(
    {
        review_score: 1
    },
    {
        name: "idx_review_score"
    }
);

db.reviews.aggregate([
    {
        $match: {
            review_score: {
                $gte: 4
            }
        }
    },
    {
        $group: {
            _id: "$review_score",
            total: {
                $sum: 1
            }
        }
    }
]).explain("executionStats");